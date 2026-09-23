import json
import logging
import re
import urllib.parse

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

BASE_URL = "https://fr.comparis.ch"
DETAIL_URL = f"{BASE_URL}/immobilien/marktplatz/details/show"

DEAL_TYPES = {BUY: 20, RENT: 10}
# comparis groups its property types under numeric roots; an empty list is "all"
ROOT_PROPERTY_TYPES = {ANY: [], HOUSE: [4], APARTMENT: [1]}

# comparis.ch is a Next.js app: the result list is server-rendered into
# __NEXT_DATA__, so the listings are read from JSON instead of from the markup.
NEXT_DATA_SELECTOR = "script#__NEXT_DATA__"


class Comparis(RealEstateWorker):
    PROBE_SELECTOR = NEXT_DATA_SELECTOR
    WAIT_FOR = (NEXT_DATA_SELECTOR,)

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "fr-CH")
        kwargs.setdefault("timezone_id", "Europe/Zurich")
        super().__init__(**kwargs)
        self.domain_name = "comparis.ch"

    def fill_empty_fields(self, real_estate_research: RealEstateResearch):
        if real_estate_research.country is None:
            real_estate_research.country = "Switzerland"

    def fetch_page(self, real_estate_research, page):
        data = self.get_result_data(self.url_builder(real_estate_research, page))
        return data.get("resultItems") or [], data.get("numberOfResults")

    def get_result_data(self, url):
        return self.parse_result_data(self.get_soup(url, wait_for=self.WAIT_FOR), url)

    def parse_result_data(self, soup, url):
        script = soup.select_one(NEXT_DATA_SELECTOR)
        if script is None:
            raise ValueError(f"{self.domain_name}: no __NEXT_DATA__ payload at {url}")
        page_props = json.loads(script.string)["props"]["pageProps"]
        # Past the last page comparis renders the route without a result list.
        return page_props.get("initialResultData") or {}

    def get_result_link(self, result):
        return f"{DETAIL_URL}/{result['AdId']}"

    def get_locality(self, result):
        # Address is a list whose first line is "1618 Châtel-St-Denis".
        address = (result.get("Address") or [""])[0]
        match = re.match(r"(\d{4})\s+(.*)", address)
        return (match.group(1), match.group(2).title()) if match else ("", address)

    def get_rooms_number(self, result):
        for fact in result.get("EssentialInformation") or []:
            match = re.match(r"([\d.,]+)\s*pièce", fact, re.I)
            if match:
                return float(match.group(1).replace(",", "."))
        return 0

    def extract_findings(self, result):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.id = str(result["AdId"])
        real_estate_item.url = self.get_result_link(result)
        real_estate_item.description = result.get("Title") or ""
        real_estate_item.platform = self.domain_name
        real_estate_item.source = result.get("PartnerName") or ""
        real_estate_item.type = result.get("PropertyTypeText") or ""
        real_estate_item.posted_date = result.get("Date") or ""

        real_estate_item.price = result.get("PriceValue") or 0
        real_estate_item.currency = self.currency_code(
            result.get("Currency"), default="CHF"
        )
        real_estate_item.price_text = result.get("Price") or ""

        real_estate_item.livable_square_meters = int(result.get("AreaValue") or 0)
        real_estate_item.rooms_number = self.get_rooms_number(result)
        real_estate_item.postal_code, real_estate_item.city = self.get_locality(result)

        coordinate = result.get("Coordinate") or {}
        real_estate_item.latitude = coordinate.get("Latitude")
        real_estate_item.longitude = coordinate.get("Longitude")

        logger.debug(f"{self.domain_name}: {real_estate_item}")
        return real_estate_item

    @staticmethod
    def location_of(real_estate_research):
        """What comparis wants in its one free-text location field.

        A canton is "Canton Vaud" - the spelling comparis puts in its own
        canton pages. A bare name means the town of that name instead, and
        nothing at all means the whole country.
        """
        if real_estate_research.region:
            return f"Canton {real_estate_research.region}"
        return real_estate_research.postal_code or real_estate_research.city

    def url_builder(self, real_estate_research: RealEstateResearch, page=1):
        if real_estate_research.url:
            # comparis pages are zero-based
            return self.with_query_param(real_estate_research.url, "page", page - 1)

        # comparis expects its whole search form as one url-encoded JSON blob;
        # only the fields we actually steer are set, the rest keeps site defaults.
        request_object = {
            "DealType": DEAL_TYPES[real_estate_research.rent_or_buy],
            "SiteId": -1,
            "RootPropertyTypes": ROOT_PROPERTY_TYPES[real_estate_research.type],
            "PropertyTypes": None,
            "LocationSearchString": self.location_of(real_estate_research),
            "Sort": 11,
        }
        query = urllib.parse.urlencode(
            {
                "requestobject": json.dumps(request_object, separators=(",", ":")),
                "page": page - 1,  # comparis pages are zero-based
            }
        )
        return f"{BASE_URL}/immobilien/result/list?{query}"
