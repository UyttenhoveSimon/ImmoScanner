import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

GEONAMES_SEARCH = "https://www.geonames.org/postalcode-search.html"
# geonames serves unclosed <tr>s; html.parser then swallows the whole table into
# the first row, so the lenient-but-structured lxml parser is used here.
GEONAMES_PARSER = "lxml"
REQUEST_TIMEOUT = 20
USER_AGENT = "ImmoScanner (+https://github.com/UyttenhoveSimon/ImmoScanner)"


class Country:
    #: provinces, cantons - whatever the country calls the tier above a town
    REGIONS = ()

    def __init__(self):
        self.alpha_2 = ""
        self.alpha_3 = ""
        self.numeric = ""
        self.name = ""
        self.official_name = ""
        self.currency = ""
        self.languages = []
        self.websites = []

    def search_postal_codes(self, query):
        """Return the geonames hits for a postal code or a place name.

        Each hit is ``{"place": ..., "postal_code": ..., "municipality": ...}``.
        """
        response = requests.get(
            GEONAMES_SEARCH,
            params={"q": query, "country": self.alpha_2},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        table = BeautifulSoup(response.text, GEONAMES_PARSER).find(
            "table", {"class": "restable"}
        )
        if table is None:
            return []

        hits = []
        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all("td", recursive=False)
            ]
            if len(cells) < 4 or not cells[0].isdigit():
                continue
            hits.append(
                {
                    "place": cells[1],
                    "postal_code": cells[2],
                    "municipality": cells[-1],
                }
            )
        return hits

    @staticmethod
    def _pick(hits, preferred=None):
        """Prefer an exact name match, then the entry that names its own municipality.

        For "5000" geonames returns both Beez and Namur; only the latter has a
        place name equal to its municipality, which is the one searches expect.
        """
        if not hits:
            return None

        if preferred:
            normalized = preferred.casefold()
            for hit in hits:
                if hit["place"].casefold() == normalized:
                    return hit

        for hit in hits:
            if hit["place"].casefold() == hit["municipality"].casefold():
                return hit

        return hits[0]

    def fetch_city_given_postal_code(self, postal_code):
        hits = [
            hit
            for hit in self.search_postal_codes(postal_code)
            if hit["postal_code"] == str(postal_code)
        ]
        hit = self._pick(hits)
        if hit is None:
            logger.warning(f"no city found for postal code {postal_code}")
            return ""
        return hit["place"]

    def fetch_postal_code_given_city(self, city):
        hits = self.search_postal_codes(urllib.parse.quote_plus(city))
        hit = self._pick(hits, preferred=city)
        if hit is None:
            logger.warning(f"no postal code found for city {city}")
            return ""
        return hit["postal_code"]

    def find_region(self, name):
        """Match a region however it was typed, or return None."""
        wanted = (name or "").casefold()
        for region in self.REGIONS:
            if region.casefold() == wanted:
                return region
        return None

    def get_real_estate_websites(self):
        return self.websites
