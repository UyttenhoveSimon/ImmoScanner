"""Portals of the AVIV group (immowelt.de, seloger.com), one card layout for all.

Their result cards carry ``data-testid`` attributes meant for the group's own
tests - far steadier than the generated class names around them. The card's
covering link has a title that sums the listing up ("Wohnung zum Kauf -
Berlin - 170.000 € - 2 Zimmer, 45 m²"), which is where the rooms and surface
are read; the address line ends with the postal code in brackets.

Checked on a capture of immowelt.de (tests/fixtures/immowelt_search.html).
seloger.com answered that capture with a DataDome wall, so its cards are
assumed to follow the same layout.
"""

import logging
import re

from price_parser import Price

from ..Intellectuals.Renovation import epc_label
from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import RealEstateWorker

logger = logging.getLogger(__name__)

CARD_PREFIX = "classified-card-mfe-"
#: French portals group thousands with a narrow no-break space
NARROW_SPACE = "\u202f"
CARD_SELECTOR = f'[data-testid^="{CARD_PREFIX}"]'


def number(text):
    """A German or French number: "74,9" is 74.9, "170.000" is 170000."""
    cleaned = text.replace(".", "").replace(NARROW_SPACE, "").replace(" ", "")
    return float(cleaned.replace(",", "."))


class AvivWorker(RealEstateWorker):
    CARD_SELECTOR = CARD_SELECTOR
    PROBE_SELECTOR = CARD_SELECTOR
    WAIT_FOR = (CARD_SELECTOR,)
    SEARCH_BY_REGION = False
    #: "9.915 Angebote" in the page title; each portal says it in its language
    TOTAL_PATTERN = r"([\d.\s\u202f]+)\s+(?:Angebote|annonces)"

    def url_builder(self, real_estate_research, page=1):
        if not real_estate_research.url:
            msg = (
                f"{self.domain_name} needs a search url copied from the site "
                "(scan --url)"
            )
            raise ValueError(msg)
        return self.with_query_param(real_estate_research.url, "page", page)

    def total_results(self, soup):
        title = soup.title.string if soup.title and soup.title.string else ""
        match = re.search(self.TOTAL_PATTERN, title)
        return int(re.sub(r"\D", "", match.group(1))) if match else None

    def text_of(self, card, test_id):
        return self.visible_text(card.select_one(f'[data-testid="{test_id}"]'))

    def extract_findings(self, card):
        item = RealEstateResearchResult()
        item.id = (card.get("data-testid") or "").removeprefix(CARD_PREFIX)
        item.platform = self.domain_name

        link = card.select_one('[data-testid="card-mfe-covering-link-testid"]')
        item.url = (link.get("href") if link else "") or ""
        summary = (link.get("title") if link else "") or ""
        body = self.text_of(card, "cardmfe-description-text-test-id")
        item.description = " — ".join(part for part in (summary, body) if part)
        item.type = summary.split(" - ")[0]

        price_text = self.text_of(card, "cardmfe-price-testid")
        # "170.000 € 3.778 €/m²": the first amount is the price
        price = Price.fromstring(price_text.split("€")[0] + "€", decimal_separator=",")
        item.price = price.amount or 0
        item.price_text = (
            price_text.split("€")[0].strip() + " €" if price.amount else ""
        )
        item.currency = "EUR"

        surface = re.search(r"([\d.,]+)\s*m²", summary)
        rooms = re.search(r"([\d,]+)\s*(?:Zimmer|pièces?)", summary)
        item.livable_square_meters = int(number(surface.group(1))) if surface else 0
        item.rooms_number = number(rooms.group(1)) if rooms else 0

        # the address line ends with the town and its postal code in brackets
        address = self.text_of(card, "cardmfe-description-box-address")
        match = re.search(r"([^,]+)\((\d{4,5})\)\s*$", address)
        if match:
            item.city, item.postal_code = match.group(1).strip(), match.group(2)
        else:
            item.city = address

        item.epc = epc_label(self.text_of(card, "card-mfe-energy-performance-class"))

        logger.debug(f"{self.domain_name}: {item}")
        return item
