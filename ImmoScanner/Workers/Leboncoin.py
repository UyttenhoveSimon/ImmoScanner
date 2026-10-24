import json
import logging
import urllib.parse

from ..Intellectuals.Renovation import epc_label
from ..Means.RealEstateResearch import ANY, APARTMENT, BUY, HOUSE, RENT
from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import RealEstateWorker

logger = logging.getLogger(__name__)

BASE_URL = "https://www.leboncoin.fr"
#: "Ventes immobilières" and "Locations"
CATEGORIES = {BUY: 9, RENT: 10}
#: leboncoin's real_estate_type values; none means every type
REAL_ESTATE_TYPES = {ANY: "1,2", HOUSE: "1", APARTMENT: "2"}
NEXT_DATA_SELECTOR = "script#__NEXT_DATA__"


def attributes_of(ad):
    """An ad's facts, which leboncoin lists as [{"key": "square", ...}, ...]."""
    return {
        attribute.get("key"): attribute.get("value")
        for attribute in ad.get("attributes") or []
        if isinstance(attribute, dict)
    }


class Leboncoin(RealEstateWorker):
    """leboncoin.fr, a Next.js app whose result list is server-rendered as JSON."""

    PROBE_SELECTOR = NEXT_DATA_SELECTOR
    WAIT_FOR = (NEXT_DATA_SELECTOR,)
    #: régions are numbered ids on leboncoin, which this scanner does not hold
    SEARCH_BY_REGION = False
    VERIFIED = False

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "fr-FR")
        kwargs.setdefault("timezone_id", "Europe/Paris")
        super().__init__(**kwargs)
        self.domain_name = "leboncoin.fr"

    def fetch_page(self, real_estate_research, page):
        soup = self.get_soup(
            self.url_builder(real_estate_research, page), wait_for=self.WAIT_FOR
        )
        script = soup.select_one(NEXT_DATA_SELECTOR)
        if script is None or not script.string:
            msg = f"{self.domain_name}: no __NEXT_DATA__ payload"
            raise ValueError(msg)
        page_props = json.loads(script.string)["props"]["pageProps"]
        search = page_props.get("searchData") or {}
        return search.get("ads") or [], search.get("total")

    def url_builder(self, real_estate_research, page=1):
        if real_estate_research.url:
            return self.with_query_param(real_estate_research.url, "page", page)

        # a town is written "Lyon_69001" in leboncoin's own location parameter
        location = "_".join(
            part
            for part in (
                real_estate_research.city.replace(" ", "-"),
                real_estate_research.postal_code,
            )
            if part
        )
        query = urllib.parse.urlencode(
            {
                "category": CATEGORIES[real_estate_research.rent_or_buy],
                "locations": location,
                "real_estate_type": REAL_ESTATE_TYPES[real_estate_research.type],
                "page": page,
            }
        )
        return f"{BASE_URL}/recherche?{query}"

    def extract_findings(self, ad):
        facts = attributes_of(ad)
        location = ad.get("location") or {}
        price = ad.get("price") or [0]

        item = RealEstateResearchResult()
        item.id = str(ad["list_id"])
        item.url = ad.get("url") or f"{BASE_URL}/ad/ventes_immobilieres/{item.id}"
        item.description = " — ".join(
            part for part in (ad.get("subject"), ad.get("body")) if part
        )
        item.platform = self.domain_name
        item.type = str(facts.get("real_estate_type") or "")
        item.posted_date = ad.get("first_publication_date") or ""

        item.price = price[0] if isinstance(price, list) else price
        item.price_text = f"{item.price:,.0f} €" if item.price else ""
        item.currency = "EUR"

        item.livable_square_meters = self.first_int(str(facts.get("square") or ""))
        item.land_square_meters = self.first_int(
            str(facts.get("land_plot_surface") or "")
        )
        item.rooms_number = self.first_int(str(facts.get("rooms") or ""))
        item.bedrooms_number = self.first_int(str(facts.get("bedrooms") or ""))
        item.postal_code = str(location.get("zipcode") or "")
        item.city = location.get("city") or ""
        item.epc = epc_label(str(facts.get("energy_rate") or ""))
        if location.get("lat") and location.get("lng"):
            item.latitude = float(location["lat"])
            item.longitude = float(location["lng"])

        logger.debug(f"{self.domain_name}: {item}")
        return item
