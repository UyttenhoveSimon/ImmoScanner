import copy
import logging
import re

from price_parser import Price

from ..Means.RealEstateResearch import ANY, APARTMENT, BUY, HOUSE, RENT
from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import RealEstateWorker

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kleinanzeigen.de"
#: (url slug, category id) per transaction and type; kleinanzeigen has no
#: category for "houses and flats", so ANY is searched as both, one after the other
CATEGORIES = {
    (BUY, HOUSE): ("s-haus-kaufen", "c208"),
    (BUY, APARTMENT): ("s-eigentumswohnung", "c196"),
    (RENT, HOUSE): ("s-haus-mieten", "c205"),
    (RENT, APARTMENT): ("s-mietwohnung", "c203"),
}


class Kleinanzeigen(RealEstateWorker):
    """kleinanzeigen.de, classified ads, many of them from private owners."""

    CARD_SELECTOR = "article.aditem"
    PROBE_SELECTOR = CARD_SELECTOR
    WAIT_FOR = (CARD_SELECTOR,)
    #: Länder are not a search kleinanzeigen offers by url
    SEARCH_BY_REGION = False
    VERIFIED = False

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "de-DE")
        kwargs.setdefault("timezone_id", "Europe/Berlin")
        super().__init__(**kwargs)
        self.domain_name = "kleinanzeigen.de"

    def get_findings(self, real_estate_research):
        if real_estate_research.type != ANY or real_estate_research.url:
            return super().get_findings(real_estate_research)
        results = []
        for kind in (HOUSE, APARTMENT):
            research = copy.copy(real_estate_research)
            research.type = kind
            results.extend(super().get_findings(research))
        return results

    def url_builder(self, real_estate_research, page=1):
        if real_estate_research.url:
            # kleinanzeigen pages are a path segment: .../seite:2/c208
            return re.sub(
                r"/(seite:\d+/)?(c\d+)", rf"/seite:{page}/\2", real_estate_research.url
            )

        slug, category = CATEGORIES[
            (real_estate_research.rent_or_buy, real_estate_research.type)
        ]
        page_segment = f"seite:{page}/" if page > 1 else ""
        return (
            f"{BASE_URL}/{slug}/{real_estate_research.postal_code}/"
            f"{page_segment}{category}"
        )

    def get_tags(self, card):
        return [self.visible_text(tag) for tag in card.select(".simpletag")]

    def extract_findings(self, card):
        item = RealEstateResearchResult()
        item.id = card.get("data-adid") or ""
        link = card.select_one("a.ellipsis") or card.select_one("h2 a")
        href = (link.get("href") if link else "") or card.get("data-href") or ""
        item.url = href if href.startswith("http") else f"{BASE_URL}{href}"
        title = self.visible_text(link)
        body = self.visible_text(card.select_one(".aditem-main--middle--description"))
        item.description = " — ".join(part for part in (title, body) if part)
        item.platform = self.domain_name

        # "350.000 € VB" - VB, Verhandlungsbasis, means the price is negotiable
        price_text = self.visible_text(
            card.select_one(".aditem-main--middle--price-shipping--price")
        )
        price = Price.fromstring(price_text, decimal_separator=",")
        item.price = price.amount or 0
        item.price_text = price_text
        item.currency = self.currency_code(price.currency, default="EUR")

        for tag in self.get_tags(card):
            if "m²" in tag and not item.livable_square_meters:
                item.livable_square_meters = self.first_int(tag.split(",")[0])
            elif re.search(r"\bZi\b|Zimmer", tag):
                match = re.search(r"\d+(?:,\d+)?", tag)
                item.rooms_number = (
                    float(match.group().replace(",", ".")) if match else 0
                )

        # "10115 Mitte"
        locality = self.visible_text(card.select_one(".aditem-main--top--left"))
        match = re.match(r"(\d{5})\s*(.*)", locality)
        item.postal_code, item.city = (
            (match.group(1), match.group(2)) if match else ("", locality)
        )

        logger.debug(f"{self.domain_name}: {item}")
        return item
