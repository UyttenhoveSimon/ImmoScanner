"""The French and German portals, on synthetic pages.

These readers were written before any page of these portals could be
captured, so the payloads below are shaped after how each portal is known to
publish its listings - they are NOT captures. They pin the extraction logic;
whether the portals still look like this is for the live tests
(``pytest -m live``) and the capture workflow to say. Replace a payload with a
real capture from ``scripts/capture_portals.py`` as soon as one exists.
"""

import json
import urllib.parse
from typing import Any

import pytest
from bs4 import BeautifulSoup

from ImmoScanner.Countries.CountryFactory import CountryFactory
from ImmoScanner.Intellectuals.Renovation import RENOVATE, assess
from ImmoScanner.Means.RealEstateResearch import (
    ANY,
    APARTMENT,
    BUY,
    HOUSE,
    RENT,
    RealEstateResearch,
)
from ImmoScanner.Workers.BienIci import BienIci
from ImmoScanner.Workers.ImmoScout24 import ImmoScout24
from ImmoScanner.Workers.Immowelt import Immowelt
from ImmoScanner.Workers.Kleinanzeigen import Kleinanzeigen
from ImmoScanner.Workers.Leboncoin import Leboncoin
from ImmoScanner.Workers.Pap import Pap
from ImmoScanner.Workers.SchemaOrg import (
    json_ld_blocks,
    listing_entries,
    number,
)
from ImmoScanner.Workers.SeLoger import SeLoger


def soup(html):
    return BeautifulSoup(html, "lxml")


def research(**kwargs):
    return RealEstateResearch(**kwargs)


class TestCountries:
    @pytest.mark.parametrize(
        ("name", "code", "domains"),
        [
            ("France", "FR", ["bienici.com", "leboncoin.fr", "seloger.com", "pap.fr"]),
            (
                "Germany",
                "DE",
                ["kleinanzeigen.de", "immobilienscout24.de", "immowelt.de"],
            ),
        ],
    )
    def test_each_country_is_registered_with_its_portals(self, name, code, domains):
        country = CountryFactory().generate_country_given_name(name)
        assert country is not None
        assert country.alpha_2 == code
        assert country.currency is not None
        assert country.currency.alpha_3 == "EUR"
        assert [site.domain_name for site in country.websites] == domains

    def test_every_new_portal_is_marked_unverified(self):
        for name in ("France", "Germany"):
            country = CountryFactory().generate_country_given_name(name)
            assert country is not None
            assert not any(site.VERIFIED for site in country.websites)

    def test_regions_are_matched_however_typed(self):
        france = CountryFactory().generate_country_given_name("France")
        germany = CountryFactory().generate_country_given_name("Germany")
        assert france is not None
        assert germany is not None
        assert france.find_region("île-de-france") == "Île-de-France"
        assert germany.find_region("BAYERN") == "Bayern"


AD: dict[str, Any] = {
    "id": "ag690001-123",
    "title": "Maison 5 pièces 120 m²",
    "description": "Maison de ville à rénover entièrement, beau potentiel.",
    "price": 189000,
    "surfaceArea": 120,
    "roomsQuantity": 5,
    "bedroomsQuantity": 3,
    "postalCode": "69001",
    "city": "Lyon 1er",
    "energyClassification": "F",
    "propertyType": "house",
    "publicationDate": "2026-10-20T08:00:00.000Z",
    "blurInfo": {"position": {"lat": 45.767, "lon": 4.834}},
}


class TestBienIci:
    @pytest.fixture
    def bienici(self):
        worker = BienIci()
        worker.zones["69001"] = ["-120965"]
        return worker

    @staticmethod
    def filters(url):
        query = urllib.parse.urlsplit(url).query
        return json.loads(urllib.parse.parse_qs(query)["filters"][0])

    def test_the_ads_url_carries_the_zone_and_the_page(self, bienici):
        url = bienici.url_builder(research(postal_code="69001", rent_or_buy=RENT), 3)
        assert url.startswith("https://www.bienici.com/realEstateAds.json?")
        filters = self.filters(url)
        assert filters["zoneIdsByTypes"] == {"zoneIds": ["-120965"]}
        assert filters["filterType"] == "rent"
        assert (filters["from"], filters["size"], filters["page"]) == (48, 24, 3)

    @pytest.mark.parametrize(
        ("kind", "expected"), [(ANY, ["house", "flat"]), (APARTMENT, ["flat"])]
    )
    def test_the_type_becomes_bienici_property_types(self, bienici, kind, expected):
        url = bienici.url_builder(research(postal_code="69001", type=kind), 1)
        assert self.filters(url)["propertyType"] == expected

    def test_a_copied_url_is_paged(self, bienici):
        url = bienici.url_builder(research(url="https://www.bienici.com/x?page=1"), 2)
        assert url.endswith("page=2")

    def test_the_zone_carrying_the_postal_code_wins(self):
        suggestions = [
            {"zoneIds": ["-1"], "postalCodes": ["69002"]},
            {"zoneIds": ["-2"], "postalCodes": ["69001"]},
        ]
        assert BienIci.pick_zone(suggestions, research(postal_code="69001")) == ["-2"]
        assert BienIci.pick_zone(suggestions, research(city="Lyon")) == ["-1"]
        assert BienIci.pick_zone([], research(city="Nowhere")) == []

    def test_zones_are_looked_up_once(self, monkeypatch):
        worker = BienIci()
        asked = []

        def get_json(url):
            asked.append(url)
            return [{"zoneIds": ["-7"], "postalCodes": ["75001"]}]

        monkeypatch.setattr(worker, "get_json", get_json)
        for _ in range(3):
            assert worker.zone_ids(research(postal_code="75001")) == ["-7"]
        assert len(asked) == 1
        assert "q=75001" in asked[0]

    def test_a_place_without_a_zone_is_refused(self, monkeypatch):
        worker = BienIci()
        monkeypatch.setattr(worker, "get_json", lambda url: [])
        with pytest.raises(ValueError, match="no zone"):
            worker.url_builder(research(city="Nowhere"), 1)

    def test_a_page_of_ads_is_read(self, bienici, monkeypatch):
        monkeypatch.setattr(
            bienici, "get_json", lambda url: {"total": 1, "realEstateAds": [AD]}
        )
        assert bienici.fetch_page(research(postal_code="69001"), 1) == ([AD], 1)

    def test_an_ad_becomes_a_listing(self, bienici):
        item = bienici.extract_findings(AD)
        assert item.url == "https://www.bienici.com/annonce/ag690001-123"
        assert (item.price, item.livable_square_meters, item.rooms_number) == (
            189000,
            120,
            5,
        )
        assert (item.postal_code, item.city, item.epc) == ("69001", "Lyon 1er", "F")
        assert (item.latitude, item.longitude) == (45.767, 4.834)
        assert assess(item)[0] == RENOVATE

    def test_a_programme_is_a_project(self, bienici):
        item = bienici.extract_findings({**AD, "price": [210000, 480000]})
        assert item.is_project
        assert (item.price, item.price_min, item.price_max) == (0, 210000, 480000)

    def test_an_ad_without_position_has_none(self, bienici):
        item = bienici.extract_findings({"id": "x", "price": 0})
        assert item.latitude is None
        assert item.price_text == ""

    def test_json_comes_through_the_browser_wrapping_too(self, monkeypatch):
        worker = BienIci()
        page = '<html><body><pre>{"total": 0, "realEstateAds": []}</pre></body></html>'
        monkeypatch.setattr(worker, "get_html", lambda url: page)
        assert worker.get_json("https://x.test") == {"total": 0, "realEstateAds": []}
        monkeypatch.setattr(worker, "get_html", lambda url: "")
        assert worker.get_json("https://x.test") == {}

    def test_only_json_counts_as_a_complete_answer(self):
        assert BienIci().looks_complete('{"a": 1}')
        assert not BienIci().looks_complete("<html>blocked</html>")


NEXT_DATA: dict[str, Any] = {
    "props": {
        "pageProps": {
            "searchData": {
                "total": 2,
                "ads": [
                    {
                        "list_id": 2934567890,
                        "subject": "Maison 4 pièces à rafraîchir",
                        "body": "Proche centre, travaux à prévoir.",
                        "url": "https://www.leboncoin.fr/ad/ventes_immobilieres/2934567890",
                        "first_publication_date": "2026-10-21 10:00:00",
                        "price": [145000],
                        "attributes": [
                            {"key": "real_estate_type", "value": "1"},
                            {"key": "square", "value": "95"},
                            {"key": "land_plot_surface", "value": "300"},
                            {"key": "rooms", "value": "4"},
                            {"key": "bedrooms", "value": "3"},
                            {"key": "energy_rate", "value": "e"},
                        ],
                        "location": {
                            "zipcode": "69001",
                            "city": "Lyon",
                            "lat": 45.77,
                            "lng": 4.83,
                        },
                    },
                    {"list_id": 1, "attributes": [], "location": {}},
                ],
            }
        }
    }
}


class TestLeboncoin:
    def test_the_search_url_names_the_town_and_the_category(self):
        url = Leboncoin().url_builder(
            research(postal_code="69001", city="Lyon", type=HOUSE, rent_or_buy=BUY), 2
        )
        assert url == (
            "https://www.leboncoin.fr/recherche?category=9&locations=Lyon_69001"
            "&real_estate_type=1&page=2"
        )

    def test_rentals_and_any_type(self):
        url = Leboncoin().url_builder(
            research(city="Saint Étienne", rent_or_buy=RENT, type=ANY), 1
        )
        assert "category=10" in url
        assert "locations=Saint-%C3%89tienne" in url
        assert "real_estate_type=1%2C2" in url

    def test_a_copied_url_is_paged(self):
        url = Leboncoin().url_builder(research(url="https://www.leboncoin.fr/r?x=1"), 4)
        assert url.endswith("page=4")

    def test_the_next_data_payload_is_read(self, monkeypatch):
        worker = Leboncoin()
        page = (
            '<script id="__NEXT_DATA__" type="application/json">'
            f"{json.dumps(NEXT_DATA)}</script>"
        )
        monkeypatch.setattr(worker, "get_soup", lambda url, wait_for=(): soup(page))
        ads, total = worker.fetch_page(research(postal_code="69001", city="Lyon"), 1)
        assert (len(ads), total) == (2, 2)

    def test_a_page_without_payload_is_an_error(self, monkeypatch):
        worker = Leboncoin()
        monkeypatch.setattr(worker, "get_soup", lambda url, wait_for=(): soup(""))
        with pytest.raises(ValueError, match="__NEXT_DATA__"):
            worker.fetch_page(research(postal_code="69001"), 1)

    def test_an_ad_becomes_a_listing(self):
        ad = NEXT_DATA["props"]["pageProps"]["searchData"]["ads"][0]
        item = Leboncoin().extract_findings(ad)
        assert item.id == "2934567890"
        assert item.price == 145000
        assert (item.livable_square_meters, item.land_square_meters) == (95, 300)
        assert (item.rooms_number, item.bedrooms_number) == (4, 3)
        assert (item.postal_code, item.city, item.epc) == ("69001", "Lyon", "E")
        assert (item.latitude, item.longitude) == (45.77, 4.83)
        assert "travaux à prévoir" in item.description

    def test_a_bare_ad_still_has_a_url(self):
        item = Leboncoin().extract_findings({"list_id": 7})
        assert item.url.endswith("/7")
        assert (item.price, item.latitude) == (0, None)


JSON_LD: dict[str, Any] = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "itemListElement": [
        {
            "@type": "ListItem",
            "position": 1,
            "item": {
                "@type": "Offer",
                "url": "https://www.seloger.com/annonces/achat/maison/lyon-1er-69/246813579.htm",
                "name": "Maison à rénover",
                "offers": {"price": "199000", "priceCurrency": "EUR"},
                "itemOffered": {
                    "@type": "House",
                    "floorSize": {"value": 110, "unitCode": "MTK"},
                    "numberOfRooms": 5,
                    "numberOfBedrooms": 3,
                    "address": {"postalCode": "69001", "addressLocality": "Lyon"},
                    "geo": {"latitude": "45.76", "longitude": "4.83"},
                },
            },
        },
        {"@type": "ListItem", "position": 2, "item": "not a listing"},
    ],
}


class TestSchemaOrg:
    def test_listings_are_found_in_an_item_list(self):
        page = soup(
            '<script type="application/ld+json">'
            f"{json.dumps(JSON_LD)}</script>"
            '<script type="application/ld+json">not json</script>'
        )
        entries = listing_entries(json_ld_blocks(page))
        assert len(entries) == 1

    def test_loose_listings_and_graphs_count_too(self):
        graph = {
            "@graph": [
                {"@type": "Apartment", "url": "https://x.test/a/12345"},
                {"@type": "Organization", "url": "https://x.test"},
            ]
        }
        page = soup(
            f'<script type="application/ld+json">[{json.dumps(graph)}]</script>'
        )
        assert len(listing_entries(json_ld_blocks(page))) == 1
        assert listing_entries(["not a dict"]) == []

    def test_an_offer_becomes_a_listing(self):
        item = SeLoger().extract_findings(JSON_LD["itemListElement"][0]["item"])
        assert item.id == "246813579"
        assert (item.price, item.currency) == (199000, "EUR")
        assert (item.livable_square_meters, item.rooms_number) == (110, 5)
        assert (item.postal_code, item.city) == ("69001", "Lyon")
        assert (item.latitude, item.longitude) == (45.76, 4.83)
        assert item.type == "House"

    def test_a_price_specification_and_an_identifier(self):
        entry = {
            "@type": "Apartment",
            "identifier": "ABC-1",
            "url": "https://www.immowelt.de/expose/abc",
            "offers": [{"priceSpecification": {"price": 1250}}],
            "floorSize": "72 m²",
        }
        item = Immowelt().extract_findings(entry)
        assert (item.id, item.price, item.livable_square_meters) == ("ABC-1", 1250, 72)
        assert item.currency == "EUR"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [(250000, 250000), ("250 000 €", 250000), ("3,5", 3.5), ({"value": 9}, 9)],
    )
    def test_numbers_are_read_however_written(self, raw, expected):
        assert number(raw) == expected

    def test_text_without_a_number_is_zero(self):
        assert number("sur demande") == 0
        assert number(None) == 0

    def test_a_portal_without_place_search_needs_a_copied_url(self):
        with pytest.raises(ValueError, match="scan --url"):
            ImmoScout24().url_builder(research(postal_code="10115"), 1)

    def test_a_copied_url_is_paged_with_the_portal_parameter(self):
        url = ImmoScout24().url_builder(
            research(url="https://www.immobilienscout24.de/Suche/de/berlin"), 2
        )
        assert url.endswith("pagenumber=2")

    def test_a_page_is_read_through_its_json_ld(self, monkeypatch):
        worker = SeLoger()
        page = soup(
            f'<script type="application/ld+json">{json.dumps(JSON_LD)}</script>'
        )
        monkeypatch.setattr(worker, "get_soup", lambda url, wait_for=(): page)
        entries, total = worker.fetch_page(research(url="https://www.seloger.com/x"), 1)
        assert (len(entries), total) == (1, None)

    def test_an_id_comes_from_the_url_when_nothing_else_names_it(self):
        assert (
            SeLoger.id_from_url("https://x.test/annonce/123456789.htm") == "123456789"
        )
        assert SeLoger.id_from_url("https://x.test/a") == "https://x.test/a"


class TestPap:
    def test_page_one_is_the_url_as_copied(self):
        url = Pap().url_builder(
            research(url="https://www.pap.fr/annonce/vente-maisons-lyon-69-g43590"), 1
        )
        assert url == "https://www.pap.fr/annonce/vente-maisons-lyon-69-g43590"

    def test_later_pages_are_a_path_suffix(self):
        worker = Pap()
        base = "https://www.pap.fr/annonce/vente-maisons-lyon-69-g43590"
        assert worker.url_builder(research(url=base), 3) == f"{base}-3"
        assert worker.url_builder(research(url=f"{base}-2"), 4) == f"{base}-4"
        assert (
            worker.url_builder(research(url=f"{base}?prix-max=300000"), 2)
            == f"{base}-2?prix-max=300000"
        )


CARD = """
<article class="aditem" data-adid="2801234567"
         data-href="/s-anzeige/haus-zu-verkaufen/2801234567-208-3331">
  <div class="aditem-main--top--left">10115 Mitte</div>
  <h2><a class="ellipsis" href="/s-anzeige/haus-zu-verkaufen/2801234567-208-3331">
    Sanierungsbedürftiges Haus</a></h2>
  <p class="aditem-main--middle--description">Altbau, Renovierung nötig.</p>
  <p class="aditem-main--middle--price-shipping--price">350.000 € VB</p>
  <span class="simpletag">120 m²</span>
  <span class="simpletag">4,5 Zi.</span>
</article>
"""


class TestKleinanzeigen:
    def test_the_search_url_is_slug_postal_code_and_category(self):
        worker = Kleinanzeigen()
        assert worker.url_builder(
            research(postal_code="10115", type=HOUSE, rent_or_buy=BUY), 1
        ) == ("https://www.kleinanzeigen.de/s-haus-kaufen/10115/c208")
        assert worker.url_builder(
            research(postal_code="10115", type=APARTMENT, rent_or_buy=RENT), 3
        ) == ("https://www.kleinanzeigen.de/s-mietwohnung/10115/seite:3/c203")

    def test_a_copied_url_is_paged_in_its_path(self):
        worker = Kleinanzeigen()
        base = "https://www.kleinanzeigen.de/s-haus-kaufen/10115/c208"
        assert worker.url_builder(research(url=base), 2) == (
            "https://www.kleinanzeigen.de/s-haus-kaufen/10115/seite:2/c208"
        )
        paged = "https://www.kleinanzeigen.de/s-haus-kaufen/10115/seite:2/c208"
        assert worker.url_builder(research(url=paged), 5).endswith("/seite:5/c208")

    def test_any_type_is_searched_as_houses_then_flats(self, monkeypatch):
        worker = Kleinanzeigen()
        asked = []
        monkeypatch.setattr(
            worker,
            "fetch_page",
            lambda searched, page: (asked.append(searched.type), ([], None))[1],
        )
        worker.get_findings(research(postal_code="10115", type=ANY))
        assert asked == [HOUSE, APARTMENT]

    def test_one_type_is_one_search(self, monkeypatch):
        worker = Kleinanzeigen()
        asked = []
        monkeypatch.setattr(
            worker,
            "fetch_page",
            lambda searched, page: (asked.append(searched.type), ([], None))[1],
        )
        worker.get_findings(research(postal_code="10115", type=HOUSE))
        assert asked == [HOUSE]

    def test_a_card_becomes_a_listing(self):
        card = soup(CARD).select_one(Kleinanzeigen.CARD_SELECTOR)
        item = Kleinanzeigen().extract_findings(card)
        assert item.id == "2801234567"
        assert item.url.startswith("https://www.kleinanzeigen.de/s-anzeige/")
        assert (item.price, item.currency) == (350000, "EUR")
        assert (item.livable_square_meters, item.rooms_number) == (120, 4.5)
        assert (item.postal_code, item.city) == ("10115", "Mitte")
        assert "Renovierung" in item.description

    def test_a_card_without_locality_code_keeps_the_text(self):
        bare = (
            '<article class="aditem" data-adid="1">'
            '<div class="aditem-main--top--left">Berlin</div></article>'
        )
        item = Kleinanzeigen().extract_findings(soup(bare).select_one("article"))
        assert (item.postal_code, item.city, item.price) == ("", "Berlin", 0)
