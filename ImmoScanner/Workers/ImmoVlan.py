import logging
import re

from price_parser import Price

from ..Means.RealEstateResearch import (
    ANY,
    APARTMENT,
    BUY,
    HOUSE,
    RENT,
    RealEstateResearch,
)
from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import RealEstateWorker

logger = logging.getLogger(__name__)

# The portal moved off immo.vlan.be (that host now answers 503 at the Akamai edge).
BASE_URL = "https://immovlan.be"
CONSENT_BUTTON = "#didomi-notice-agree-button"
TRANSACTIONS = {BUY: "a-vendre", RENT: "a-louer"}
# immovlan lists every type when propertytypes is left out
PROPERTY_TYPES = {ANY: "", HOUSE: "maison", APARTMENT: "appartement"}


class ImmoVlan(RealEstateWorker):
    CARD_SELECTOR = "article.v3-search-card"
    PROBE_SELECTOR = CARD_SELECTOR
    WAIT_FOR = (CARD_SELECTOR,)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.domain_name = "immovlan.be"

    def fill_empty_fields(self, real_estate_research: RealEstateResearch):
        if real_estate_research.country is None:
            real_estate_research.country = "Belgique"

    def fetch_page(self, real_estate_research, page):
        items, total = super().fetch_page(real_estate_research, page)
        # only reachable on the browser path, and never worth failing over
        self.dismiss_banner(CONSENT_BUTTON)
        return items, total

    def total_results(self, soup):
        # "30 résultats (1 - 20)"
        counter = soup.select_one(".v3-search-result-count")
        if counter is None:
            return None
        return self.first_int(self.visible_text(counter)) or None

    def get_result_id(self, result):
        # The listing reference is the last segment of the detail URL ("vbe67521");
        # the favourite button carries the same reference, upper-cased.
        reference = self.get_result_link(result).rstrip("/").split("/")[-1]
        if reference:
            return reference.upper()
        favorite = result.select_one("button.v3-search-card-favorite[data-value-id]")
        return favorite["data-value-id"] if favorite else ""

    def get_result_description(self, result):
        return self.visible_text(result.select_one("p.v3-search-card-description"))

    def get_result_link(self, result):
        href = result.get("data-url") or ""
        if not href:
            link = result.select_one("h2.v3-search-card-title a")
            href = link.get("href", "") if link else ""
        return href if href.startswith("http") else f"{BASE_URL}{href}"

    def get_pill(self, result, unit_pattern):
        """Read a highlight pill such as "<strong>541</strong> m²"."""
        for pill in result.select("span.v3-search-card-pill"):
            text = self.visible_text(pill)
            if re.search(unit_pattern, text, re.I):
                value = pill.select_one("strong")
                return self.first_int(value.get_text(strip=True) if value else text)
        return 0

    def get_bedrooms_number(self, result):
        # The card also publishes schema.org microdata, which is stabler than the pills.
        meta = result.select_one("meta[itemprop='numberOfBedrooms']")
        if meta and meta.get("content"):
            return self.first_int(meta["content"])
        return self.get_pill(result, r"chambre")

    def get_livable_square_meters(self, result):
        return self.get_pill(result, r"m²")

    def get_locality(self, result):
        postal = result.select_one("[itemprop='postalCode']")
        city = result.select_one("[itemprop='addressLocality']")
        return (
            postal.get_text(strip=True) if postal else "",
            city.get_text(strip=True).title() if city else "",
        )

    def get_result_price(self, result):
        return Price.fromstring(
            self.visible_text(result.select_one("span.v3-search-card-price"))
        )

    def extract_findings(self, result):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.url = self.get_result_link(result)
        real_estate_item.id = self.get_result_id(result)
        real_estate_item.description = self.get_result_description(result)
        real_estate_item.platform = self.domain_name
        real_estate_item.type = (result.get("itemtype") or "").rsplit("/", 1)[-1]

        price = self.get_result_price(result)
        real_estate_item.price_obj = price
        real_estate_item.price = price.amount
        real_estate_item.currency = self.currency_code(price.currency)
        real_estate_item.price_text = price.amount_text

        real_estate_item.bedrooms_number = self.get_bedrooms_number(result)
        real_estate_item.livable_square_meters = self.get_livable_square_meters(result)
        real_estate_item.postal_code, real_estate_item.city = self.get_locality(result)

        logger.debug(f"{self.domain_name}: {real_estate_item}")
        return real_estate_item

    def url_builder(self, real_estate_research: RealEstateResearch, page=1):
        if real_estate_research.url:
            return self.with_query_param(real_estate_research.url, "page", page)

        town = f"{real_estate_research.postal_code}-{real_estate_research.city.lower()}"
        url = (
            f"{BASE_URL}/fr/immobilier"
            f"?transactiontypes={TRANSACTIONS[real_estate_research.rent_or_buy]}"
            f"&propertytypes={PROPERTY_TYPES[real_estate_research.type]}"
            f"&towns={town}&noindex=1"
        )
        return url if page == 1 else f"{url}&page={page}"
