"""kleinanzeigen.de, classified ads, many of them from private owners.

Its search urls key a place by an internal location id ("/c196l3331"); a
postal code alone in the path is ignored, and the search silently covers all
of Germany. So the first page goes through the site's own search form,
which redirects to the coded url, and the later pages are walked from the
canonical url that first page names.

The cards are styled with generated utility classes, so they are read by what
their text says - "12055 Neukölln", "61,16 m² · 2 Zi.", "340.000 € VB" - not
by class names. Checked on a capture (tests/fixtures/kleinanzeigen_search.html).
"""

import copy
import logging
import re
import urllib.parse

from price_parser import Price

from ..Means.RealEstateResearch import ANY, APARTMENT, BUY, HOUSE, RENT
from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import RealEstateWorker

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kleinanzeigen.de"
SEARCH_FORM = f"{BASE_URL}/s-suchanfrage.html"
#: category ids per transaction and type; there is no "houses and flats"
#: category, so ANY is searched as both, one after the other
CATEGORIES = {
    (BUY, HOUSE): 208,
    (BUY, APARTMENT): 196,
    (RENT, HOUSE): 205,
    (RENT, APARTMENT): 203,
}
CARD_SELECTOR = "article[data-adid]"

LOCALITY = re.compile(r"^(\d{5})\s+(.+)$")
PRICE = re.compile(r"^[\d.]+\s*€")
SURFACE = re.compile(r"([\d.,]+)\s*m²")
ROOMS = re.compile(r"([\d,]+)\s*Zi\b")
TOTAL = re.compile(r"von\s+([\d.]+)")


def german_number(text):
    return float(text.replace(".", "").replace(",", "."))


def with_page(url, page):
    """Kleinanzeigen pages are a path segment: .../seite:2/c196l3331."""
    parts = urllib.parse.urlsplit(url)
    path = re.sub(r"/seite:\d+", "", parts.path)
    if page > 1:
        path = re.sub(r"/(c\d+[^/]*)$", rf"/seite:{page}/\1", path)
    return urllib.parse.urlunsplit(parts._replace(path=path))


class Kleinanzeigen(RealEstateWorker):
    CARD_SELECTOR = CARD_SELECTOR
    PROBE_SELECTOR = CARD_SELECTOR
    WAIT_FOR = (CARD_SELECTOR,)
    #: Länder are not a search kleinanzeigen offers by url
    SEARCH_BY_REGION = False
    #: checked on captures, page 2 included (tests/fixtures/kleinanzeigen_search.html)
    VERIFIED = True

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "de-DE")
        kwargs.setdefault("timezone_id", "Europe/Berlin")
        super().__init__(**kwargs)
        self.domain_name = "kleinanzeigen.de"
        #: the coded search url the form redirected to, per search
        self.resolved = {}

    def get_findings(self, real_estate_research):
        if real_estate_research.type != ANY or real_estate_research.url:
            return super().get_findings(real_estate_research)
        results = []
        for kind in (HOUSE, APARTMENT):
            research = copy.copy(real_estate_research)
            research.type = kind
            results.extend(super().get_findings(research))
        return results

    @staticmethod
    def key_of(real_estate_research):
        return (
            real_estate_research.postal_code or real_estate_research.city,
            real_estate_research.rent_or_buy,
            real_estate_research.type,
        )

    def url_builder(self, real_estate_research, page=1):
        if real_estate_research.url:
            return with_page(real_estate_research.url, page)

        resolved = self.resolved.get(self.key_of(real_estate_research))
        if page > 1 and resolved:
            return with_page(resolved, page)

        query = urllib.parse.urlencode(
            {
                "categoryId": CATEGORIES[
                    (real_estate_research.rent_or_buy, real_estate_research.type)
                ],
                "locationStr": real_estate_research.postal_code
                or real_estate_research.city,
                "radius": 0,
                "pageNum": page,
                "action": "find",
            }
        )
        return f"{SEARCH_FORM}?{query}"

    def fetch_page(self, real_estate_research, page):
        soup = self.get_soup(
            self.url_builder(real_estate_research, page), wait_for=self.WAIT_FOR
        )
        canonical = soup.select_one('link[rel="canonical"]')
        if page == 1 and canonical and canonical.get("href"):
            self.resolved[self.key_of(real_estate_research)] = canonical["href"]
        return soup.select(self.CARD_SELECTOR), self.total_results(soup)

    def total_results(self, soup):
        # "1 - 25 von 72.968 Eigentumswohnung kaufen in Deutschland"
        heading = self.visible_text(soup.select_one("h1"))
        match = TOTAL.search(heading)
        return int(match.group(1).replace(".", "")) if match else None

    def extract_findings(self, card):
        for script in card.select("script"):
            script.decompose()
        lines = [re.sub(r"\s+", " ", text) for text in card.stripped_strings]

        item = RealEstateResearchResult()
        item.id = card.get("data-adid") or ""
        href = card.get("data-href") or ""
        item.url = href if href.startswith("http") else f"{BASE_URL}{href}"
        item.platform = self.domain_name

        # the picture links to the ad too, with its photo count as text
        title = max(
            (self.visible_text(link) for link in card.select('a[href*="/s-anzeige/"]')),
            key=len,
            default="",
        )
        # the teaser is the one long line of the card
        teaser = max((line for line in lines if line != title), key=len, default="")
        item.description = " — ".join(part for part in (title, teaser) if part)

        for line in lines:
            locality = LOCALITY.match(line)
            if locality and not item.postal_code:
                item.postal_code, item.city = locality.group(1), locality.group(2)
            elif PRICE.match(line) and not item.price:
                # "290.000 € VB": VB, Verhandlungsbasis, means negotiable
                price = Price.fromstring(line, decimal_separator=",")
                item.price = price.amount or 0
                item.price_text = line
            elif "m²" in line and ("·" in line or ROOMS.search(line)):
                surface = SURFACE.search(line)
                rooms = ROOMS.search(line)
                if surface and not item.livable_square_meters:
                    item.livable_square_meters = int(german_number(surface.group(1)))
                if rooms:
                    item.rooms_number = german_number(rooms.group(1))
        item.currency = "EUR"

        logger.debug(f"{self.domain_name}: {item}")
        return item
