"""Extraction tests against search pages captured from the live portals.

These are the tests that catch a portal redesign: they fail on the exact
selectors and payload keys the workers depend on, without touching the network.
Refresh a fixture with a real capture when a portal changes for good.
"""

import pytest

from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb


@pytest.fixture
def immoweb():
    return Immoweb()


@pytest.fixture
def immovlan():
    return ImmoVlan()


@pytest.fixture
def comparis():
    return Comparis()


class TestImmoweb:
    def test_reads_every_card(self, immoweb, soup_of):
        soup = soup_of("immoweb_search.html")
        assert len(soup.select(immoweb.CARD_SELECTOR)) == 3

    def test_extracts_from_the_embedded_json(self, immoweb, soup_of):
        cards = soup_of("immoweb_search.html").select(immoweb.CARD_SELECTOR)
        results = [immoweb.extract_findings(card) for card in cards]
        properties = [result for result in results if not result.is_project]
        assert properties

        for result in properties:
            assert result.id.isdigit()
            assert result.url.startswith("https://www.immoweb.be/fr/annonce/")
            assert result.price > 0
            assert result.currency == "EUR"
            assert result.postal_code == "5000"
            assert result.city
            assert result.platform == "immoweb.be"
            assert result.livable_square_meters > 0

        # The JSON path is the only one that yields a position, and immoweb
        # leaves it out of its sponsored cards.
        assert any(result.latitude and result.longitude for result in results)
        assert all(
            (result.geo_fingerprint() is None) == (result.latitude is None)
            for result in results
        )

    def test_keeps_new_build_projects_out_of_the_statistics(self, immoweb, soup_of):
        """A development is advertised as "230 000 € - 745 000 €", not a price."""
        cards = soup_of("immoweb_search.html").select(immoweb.CARD_SELECTOR)
        projects = [
            result
            for result in (immoweb.extract_findings(card) for card in cards)
            if result.is_project
        ]
        assert projects

        for project in projects:
            assert project.price == 0  # never averaged into a median
            assert project.price_min and project.price_max
            assert project.price_min < project.price_max
            assert "-" in project.price_text

    def test_extracts_from_hydrated_markup(self, immoweb, soup_of):
        """The browser path sees markup only: Vue drops the JSON on hydration."""
        cards = soup_of("immoweb_search_hydrated.html").select(immoweb.CARD_SELECTOR)
        assert cards
        assert not any(card.find(attrs={":classified": True}) for card in cards)

        for card in cards:
            result = immoweb.extract_findings(card)
            assert result.id.isdigit()
            assert result.price > 0
            assert result.livable_square_meters > 0
            assert result.postal_code == "5000"

    def test_reads_the_total_off_the_title(self, immoweb, soup_of):
        assert immoweb.total_results(soup_of("immoweb_search.html")) == 364

    def test_paginates_a_user_supplied_url(self, immoweb):
        from ImmoScanner.Means.RealEstateResearch import RealEstateResearch

        research = RealEstateResearch(url="https://www.immoweb.be/fr/recherche?page=1")
        assert immoweb.url_builder(research, 3).endswith("page=3")


class TestImmoVlan:
    def test_extracts_cards(self, immovlan, soup_of):
        cards = soup_of("immovlan_search.html").select(immovlan.CARD_SELECTOR)
        assert len(cards) == 3

        for card in cards:
            result = immovlan.extract_findings(card)
            assert result.id.startswith("VBE")
            assert result.url.startswith("https://immovlan.be/fr/detail/")
            assert result.price > 0
            assert result.currency == "EUR"
            assert result.postal_code == "5000"
            assert result.platform == "immovlan.be"

    def test_reads_bedrooms_from_microdata(self, immovlan, soup_of):
        card = soup_of("immovlan_search.html").select(immovlan.CARD_SELECTOR)[0]
        result = immovlan.extract_findings(card)
        assert result.bedrooms_number > 0
        assert result.livable_square_meters > 0

    def test_reads_the_announced_total(self, immovlan, soup_of):
        assert immovlan.total_results(soup_of("immovlan_search.html")) == 30


class TestComparis:
    def test_extracts_items_from_next_data(self, comparis, soup_of):
        soup = soup_of("comparis_search.html")
        data = comparis.parse_result_data(soup, "fixture")
        assert data["numberOfResults"] == 72

        for item in data["resultItems"]:
            result = comparis.extract_findings(item)
            assert result.id.isdigit()
            assert result.url.startswith(
                "https://fr.comparis.ch/immobilien/marktplatz/details/show/"
            )
            assert result.price > 0
            assert result.currency == "CHF"
            assert result.postal_code == "1618"
            assert result.source  # the portal comparis aggregated it from

    def test_reads_rooms_and_position(self, comparis, soup_of):
        soup = soup_of("comparis_search.html")
        item = comparis.parse_result_data(soup, "fixture")["resultItems"][0]
        result = comparis.extract_findings(item)
        assert result.rooms_number == 4.5
        assert result.latitude and result.longitude

    def test_tolerates_a_page_past_the_last(self, comparis, soup_of):
        """Comparis renders the route without a result list past the last page."""
        from bs4 import BeautifulSoup

        empty = BeautifulSoup(
            '<script id="__NEXT_DATA__">{"props":{"pageProps":{}}}</script>', "lxml"
        )
        assert comparis.parse_result_data(empty, "fixture") == {}
