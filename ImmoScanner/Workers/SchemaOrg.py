"""Read listings from the schema.org data portals publish for search engines.

A portal can redesign its cards every quarter, but the JSON-LD it embeds for
Google follows a public vocabulary: an ``ItemList`` of residences or offers,
each with a url, a price, a floor size and an address. That makes it the most
stable thing to read on a portal whose own markup is not known - and the
first thing to check when one of these readers comes back empty.
"""

import json
import logging
import re

from ..Means.RealEstateResearchResult import RealEstateResearchResult
from .RealEstateWorker import RealEstateWorker

logger = logging.getLogger(__name__)

JSON_LD_SELECTOR = 'script[type="application/ld+json"]'
#: schema.org types a listing is published under
LISTING_TYPES = {
    "Accommodation",
    "Apartment",
    "House",
    "Offer",
    "Product",
    "RealEstateListing",
    "Residence",
    "SingleFamilyResidence",
}


def json_ld_blocks(soup):
    """Every JSON-LD object on the page, @graph members included."""
    blocks = []
    for script in soup.select(JSON_LD_SELECTOR):
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        for block in data if isinstance(data, list) else [data]:
            if isinstance(block, dict):
                blocks.extend(block.get("@graph") or [block])
    return blocks


def types_of(entry):
    kind = entry.get("@type") or []
    return set(kind if isinstance(kind, list) else [kind])


def listing_entries(blocks):
    """The listings among the blocks: members of an ItemList, or loose ones."""
    entries = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if "ItemList" in types_of(block):
            for element in block.get("itemListElement") or []:
                if isinstance(element, dict):
                    item = element.get("item", element)
                    if isinstance(item, dict):
                        entries.append(item)
        elif types_of(block) & LISTING_TYPES and block.get("url"):
            entries.append(block)
    return entries


def first(value):
    return value[0] if isinstance(value, list) and value else value


def number(value):
    """A number out of 250000, "250000", "250 000 €" or {"value": 90}."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (int, float)):
        return value
    match = re.search(r"\d[\d\s.,]*", str(value or ""))
    if not match:
        return 0
    digits = re.sub(r"[\s.]", "", match.group()).replace(",", ".")
    try:
        return float(digits)
    except ValueError:
        return 0


def subject_of(entry):
    """A RealEstateListing describes its property under "about"/"mainEntity"."""
    for key in ("about", "mainEntity", "itemOffered"):
        inner = first(entry.get(key))
        if isinstance(inner, dict):
            return inner
    return {}


def price_of(entry):
    offers = first(entry.get("offers")) or {}
    if not isinstance(offers, dict):
        offers = {}
    specification = first(offers.get("priceSpecification")) or {}
    price = (
        offers.get("price")
        or (specification.get("price") if isinstance(specification, dict) else None)
        or entry.get("price")
    )
    currency = offers.get("priceCurrency") or entry.get("priceCurrency") or ""
    return number(price), currency


class SchemaOrgWorker(RealEstateWorker):
    """A portal read through its JSON-LD; subclasses say where its searches live."""

    PROBE_SELECTOR = JSON_LD_SELECTOR
    #: these portals' own search urls are not built here: copy one from the site
    SEARCH_BY_PLACE = False
    SEARCH_BY_REGION = False
    VERIFIED = False
    #: the query parameter that pages a search url on this portal
    PAGE_PARAMETER = "page"
    DEFAULT_CURRENCY = "EUR"

    def fetch_page(self, real_estate_research, page):
        soup = self.get_soup(
            self.url_builder(real_estate_research, page), wait_for=self.WAIT_FOR
        )
        return listing_entries(json_ld_blocks(soup)), None

    def url_builder(self, real_estate_research, page=1):
        if not real_estate_research.url:
            msg = (
                f"{self.domain_name} needs a search url copied from the site "
                "(scan --url)"
            )
            raise ValueError(msg)
        return self.with_query_param(
            real_estate_research.url, self.PAGE_PARAMETER, page
        )

    def extract_findings(self, entry):
        item = RealEstateResearchResult()
        subject = subject_of(entry)
        merged = {**subject, **entry}

        item.url = str(merged.get("url") or "")
        item.id = str(
            merged.get("identifier") or merged.get("sku") or self.id_from_url(item.url)
        )
        item.description = merged.get("name") or merged.get("description") or ""
        item.platform = self.domain_name
        item.type = " ".join(sorted(types_of(subject or entry) - {"Offer", "Product"}))

        price, currency = price_of(entry)
        item.price = price
        item.price_text = f"{price:,.0f}" if price else ""
        item.currency = self.currency_code(currency, default=self.DEFAULT_CURRENCY)

        item.livable_square_meters = int(number(merged.get("floorSize")))
        item.rooms_number = number(merged.get("numberOfRooms"))
        item.bedrooms_number = int(number(merged.get("numberOfBedrooms")))

        address = first(merged.get("address")) or {}
        if isinstance(address, dict):
            item.postal_code = str(address.get("postalCode") or "")
            item.city = address.get("addressLocality") or ""

        geo = merged.get("geo") or {}
        if isinstance(geo, dict) and geo.get("latitude") and geo.get("longitude"):
            item.latitude = float(geo["latitude"])
            item.longitude = float(geo["longitude"])

        logger.debug(f"{self.domain_name}: {item}")
        return item

    @staticmethod
    def id_from_url(url):
        """The listing number every portal puts at the end of its detail urls."""
        numbers = re.findall(r"\d{5,}", url or "")
        return numbers[-1] if numbers else url
