import json
import logging
import urllib.parse

from bs4 import BeautifulSoup

from ..Intellectuals.Renovation import epc_label
from ..Means.RealEstateResearch import ANY, APARTMENT, BUY, HOUSE, RENT
from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import HTML_PARSER, RealEstateWorker

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bienici.com"
ADS_URL = f"{BASE_URL}/realEstateAds.json"
SUGGEST_URL = "https://res.bienici.com/suggest.json"
PAGE_SIZE = 24
FILTER_TYPES = {BUY: "buy", RENT: "rent"}
PROPERTY_TYPES = {ANY: ["house", "flat"], HOUSE: ["house"], APARTMENT: ["flat"]}


class BienIci(RealEstateWorker):
    """bienici.com, read through the JSON api its own pages call.

    A place is first turned into bienici's zone ids by its suggestion api,
    then the ads of those zones are asked for, a page at a time.
    """

    #: checked on a capture (tests/fixtures/bienici_search.json)
    VERIFIED = True

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "fr-FR")
        kwargs.setdefault("timezone_id", "Europe/Paris")
        super().__init__(**kwargs)
        self.domain_name = "bienici.com"
        self.zones = {}

    def looks_complete(self, html):
        try:
            json.loads(html)
        except ValueError:
            return False
        return True

    def get_json(self, url):
        text = self.get_html(url)
        self.raise_on_bot_wall(text)
        if text.lstrip().startswith("<"):
            # the browser rung wraps a JSON answer in a page of its own
            text = BeautifulSoup(text, HTML_PARSER).get_text()
        return json.loads(text) if text.strip() else {}

    def zone_ids(self, real_estate_research):
        """Zone ids bienici gives the place or région searched, looked up once."""
        place = (
            real_estate_research.region
            or real_estate_research.postal_code
            or real_estate_research.city
        )
        if place not in self.zones:
            query = urllib.parse.urlencode({"q": place})
            suggestions = self.get_json(f"{SUGGEST_URL}?{query}") or []
            self.zones[place] = self.pick_zone(suggestions, real_estate_research)
        return self.zones[place]

    @staticmethod
    def pick_zone(suggestions, real_estate_research):
        """Prefer the suggestion carrying the asked postal code, else the first."""
        code = real_estate_research.postal_code
        for suggestion in suggestions:
            if code and code in (suggestion.get("postalCodes") or []):
                return list(suggestion.get("zoneIds") or [])
        return list(suggestions[0].get("zoneIds") or []) if suggestions else []

    def fetch_page(self, real_estate_research, page):
        data = self.get_json(self.url_builder(real_estate_research, page)) or {}
        return data.get("realEstateAds") or [], data.get("total")

    def url_builder(self, real_estate_research, page=1):
        if real_estate_research.url:
            return self.with_query_param(real_estate_research.url, "page", page)

        zones = self.zone_ids(real_estate_research)
        if not zones:
            msg = f"{self.domain_name} knows no zone for this place"
            raise ValueError(msg)
        filters = {
            "size": PAGE_SIZE,
            "from": (page - 1) * PAGE_SIZE,
            "page": page,
            "filterType": FILTER_TYPES[real_estate_research.rent_or_buy],
            "propertyType": PROPERTY_TYPES[real_estate_research.type],
            "onTheMarket": [True],
            "sortBy": "relevance",
            "sortOrder": "desc",
            "zoneIdsByTypes": {"zoneIds": zones},
        }
        query = urllib.parse.urlencode(
            {"filters": json.dumps(filters, separators=(",", ":"))}
        )
        return f"{ADS_URL}?{query}"

    def extract_findings(self, ad):
        item = RealEstateResearchResult()
        item.id = str(ad["id"])
        item.url = f"{BASE_URL}/annonce/{item.id}"
        # the title says "Maison 5 pièces"; the condition is in the description
        item.description = " — ".join(
            part for part in (ad.get("title"), ad.get("description")) if part
        )
        item.platform = self.domain_name
        item.type = ad.get("propertyType") or ""
        item.posted_date = ad.get("publicationDate") or ""

        # a new-build programme quotes a range for the whole building
        price = ad.get("price")
        if isinstance(price, list):
            item.is_project = True
            item.price = 0
            item.price_min, item.price_max = min(price), max(price)
        else:
            item.price = price or 0
        item.price_text = f"{item.price:,.0f} €" if item.price else ""
        item.currency = "EUR"

        item.livable_square_meters = int(ad.get("surfaceArea") or 0)
        item.rooms_number = ad.get("roomsQuantity") or 0
        item.bedrooms_number = ad.get("bedroomsQuantity") or 0
        item.postal_code = str(ad.get("postalCode") or "")
        item.city = ad.get("city") or ""
        item.epc = epc_label(ad.get("energyClassification"))

        # bienici blurs the position of most ads; a blurred point is still the
        # right neighbourhood, which is all the map and the dedup need
        position = (ad.get("blurInfo") or {}).get("position") or {}
        if position.get("lat") and position.get("lon"):
            item.latitude = float(position["lat"])
            item.longitude = float(position["lon"])

        logger.debug(f"{self.domain_name}: {item}")
        return item
