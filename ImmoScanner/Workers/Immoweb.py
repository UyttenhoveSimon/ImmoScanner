import json
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

BASE_URL = "https://www.immoweb.be"
# Server-rendered cards carry the whole listing as JSON on their Vue component;
# it holds the surface, the bedroom count and the coordinates, none of which the
# markup exposes reliably. Hydration removes the attribute, so the browser path
# still needs the markup reader below.
CLASSIFIED_ATTRIBUTE = ":classified"
TRANSACTIONS = {BUY: "a-vendre", RENT: "a-louer"}
# "maison-et-appartement" is immoweb's own catch-all segment; an unknown one
# silently falls back to houses only.
PROPERTY_TYPES = {
    ANY: "maison-et-appartement",
    HOUSE: "maison",
    APARTMENT: "appartement",
}


class Immoweb(RealEstateWorker):
    CARD_SELECTOR = "article.card--result"
    PROBE_SELECTOR = CARD_SELECTOR
    WAIT_FOR = (CARD_SELECTOR,)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.domain_name = "immoweb.be"

    def fill_empty_fields(self, real_estate_research: RealEstateResearch):
        if real_estate_research.country is None:
            real_estate_research.country = "Belgique"

    def total_results(self, soup):
        # "129 MAISONS à vendre à Namur (5000) - Immoweb". The heading carrying
        # the same count is hydrated client-side and absent from a plain GET.
        title = soup.title.string if soup.title else ""
        return self.first_int(title) or None

    def get_result_id(self, result):
        # ids on the page are "classified_21841479" but also "premium_position_21803099",
        # so the classified number is read back from the listing link instead.
        match = re.search(r"/(\d+)/?$", self.get_result_link(result))
        return match.group(1) if match else result.get("id", "")

    def get_result_description(self, result):
        return self.visible_text(result.select_one(".card--result__description"))

    def get_result_link(self, result):
        link = result.select_one("a.card__title-link")
        href = link.get("href", "") if link else ""
        if not href:
            return ""
        return href if href.startswith("http") else f"{BASE_URL}{href}"

    def get_property_information(self, result):
        # e.g. "4 ch. · 140 m²"
        return self.visible_text(result.select_one("p.card__information--property"))

    def get_bedrooms_number(self, result):
        match = re.search(r"(\d+)\s*ch", self.get_property_information(result))
        return int(match.group(1)) if match else 0

    def get_livable_square_meters(self, result):
        match = re.search(r"(\d[\d\s.]*)\s*m²", self.get_property_information(result))
        return self.first_int(match.group(1)) if match else 0

    def get_locality(self, result):
        # "5000 NAMUR"
        text = self.visible_text(
            result.select_one("p.card--results__information--locality")
        )
        match = re.match(r"(\d{4})\s+(.*)", text)
        return (match.group(1), match.group(2).title()) if match else ("", text)

    def get_result_price(self, result):
        # The .sr-only span carries the unformatted amount ("199000€").
        screen_reader_price = result.select_one(".card--result__price .sr-only")
        if screen_reader_price:
            return Price.fromstring(screen_reader_price.get_text(strip=True))
        return Price.fromstring(
            self.visible_text(result.select_one(".card--result__price"))
        )

    def extract_findings(self, result):
        component = result.find(attrs={CLASSIFIED_ATTRIBUTE: True})
        if component is not None:
            real_estate_item = self.extract_from_classified(
                result, json.loads(component[CLASSIFIED_ATTRIBUTE])
            )
        else:
            real_estate_item = self.extract_from_markup(result)

        logger.debug(f"{self.domain_name}: {real_estate_item}")
        return real_estate_item

    def extract_from_classified(self, result, classified):
        real_estate_item = RealEstateResearchResult()
        property_ = classified.get("property") or {}
        location = property_.get("location") or {}
        price = classified.get("price") or {}

        real_estate_item.id = str(classified.get("id", ""))
        real_estate_item.url = self.get_result_link(result)
        real_estate_item.description = property_.get("title") or ""
        real_estate_item.platform = self.domain_name
        real_estate_item.type = (property_.get("subtype") or "").title()
        real_estate_item.posted_date = (classified.get("publication") or {}).get(
            "lastModificationDate"
        ) or ""

        real_estate_item.price_text = price.get("mainDisplayPrice") or ""
        real_estate_item.currency = "EUR"

        # New-build developments advertise "230 000 € - 745 000 €" for a whole
        # building. Averaging that into a price per property would be wrong, so
        # the range is kept and the price left unset.
        cluster = classified.get("cluster") or {}
        real_estate_item.price = price.get("mainValue") or 0
        real_estate_item.is_project = real_estate_item.price == 0 and bool(
            price.get("minRangeValue") or cluster.get("minPrice")
        )
        if real_estate_item.is_project:
            real_estate_item.price_min = (
                price.get("minRangeValue") or cluster.get("minPrice") or 0
            )
            real_estate_item.price_max = (
                price.get("maxRangeValue") or cluster.get("maxPrice") or 0
            )

        real_estate_item.livable_square_meters = (
            property_.get("netHabitableSurface") or 0
        )
        real_estate_item.bedrooms_number = property_.get("bedroomCount") or 0
        real_estate_item.rooms_number = property_.get("roomCount") or 0
        real_estate_item.postal_code = location.get("postalCode") or ""
        real_estate_item.city = (location.get("locality") or "").title()
        real_estate_item.latitude = location.get("latitude")
        real_estate_item.longitude = location.get("longitude")

        return real_estate_item

    def extract_from_markup(self, result):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.url = self.get_result_link(result)
        real_estate_item.id = self.get_result_id(result)
        real_estate_item.description = self.get_result_description(result)
        real_estate_item.platform = self.domain_name
        real_estate_item.type = self.visible_text(
            result.select_one(".card__title-link")
        )

        price = self.get_result_price(result)
        real_estate_item.price_obj = price
        real_estate_item.price = price.amount
        real_estate_item.currency = self.currency_code(price.currency)
        real_estate_item.price_text = price.amount_text

        real_estate_item.bedrooms_number = self.get_bedrooms_number(result)
        real_estate_item.livable_square_meters = self.get_livable_square_meters(result)
        real_estate_item.postal_code, real_estate_item.city = self.get_locality(result)

        return real_estate_item

    def url_builder(self, real_estate_research: RealEstateResearch, page=1):
        if real_estate_research.url:
            return self.with_query_param(real_estate_research.url, "page", page)

        # Searching by postal code alone. immoweb also accepts a
        # /<city>/<postal code> path but keys off the postal code and ignores
        # the name - and an apostrophe in it ("Braine-L'Alleud") silently
        # returned a generic page with no result at all.
        return (
            f"{BASE_URL}/fr/recherche/{PROPERTY_TYPES[real_estate_research.type]}"
            f"/{TRANSACTIONS[real_estate_research.rent_or_buy]}"
            f"?countries=BE&postalCodes={real_estate_research.postal_code}"
            f"&page={page}"
        )
