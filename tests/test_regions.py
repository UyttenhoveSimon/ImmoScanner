"""Searching a whole province or canton rather than one locality."""

import urllib.parse

import pytest

from ImmoScanner.Countries.Belgium import Belgium
from ImmoScanner.Countries.Country import Country
from ImmoScanner.Countries.Switzerland import Switzerland
from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Means.RealEstateResearch import APARTMENT, RENT, RealEstateResearch
from ImmoScanner.Showrooms.Explorer import Explorer
from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb


class TestDeclaring:
    def test_belgium_has_its_eleven_provinces(self):
        assert len(Belgium.REGIONS) == 11
        assert "Brabant wallon" in Belgium.REGIONS

    def test_switzerland_has_its_twenty_six_cantons(self):
        assert len(Switzerland.REGIONS) == 26
        assert "Vaud" in Switzerland.REGIONS

    def test_schwyz_keeps_the_spelling_comparis_knows(self):
        """ "Schwytz", the French form, returns nothing there."""
        assert "Schwyz" in Switzerland.REGIONS
        assert "Schwytz" not in Switzerland.REGIONS

    def test_a_region_is_matched_however_it_is_typed(self):
        assert Belgium().find_region("brabant WALLON") == "Brabant wallon"
        assert Switzerland().find_region("vaud") == "Vaud"

    def test_a_region_nobody_has_is_not_matched(self):
        assert Belgium().find_region("Atlantide") is None
        assert Belgium().find_region("") is None

    def test_a_country_with_no_regions_declared_matches_none(self):
        assert Country().find_region("anything") is None


class TestSearchUrls:
    def test_immoweb_puts_the_province_in_the_path(self):
        url = Immoweb().url_builder(RealEstateResearch(region="Brabant wallon"), 2)
        assert "/brabant-wallon/province?" in url
        assert "page=2" in url
        assert "postalCodes" not in url

    def test_immovlan_names_the_province_in_its_own_parameter(self):
        url = ImmoVlan().url_builder(RealEstateResearch(region="Brabant wallon"), 1)
        assert "provinces=brabant-wallon" in url
        assert "towns=" not in url

    @pytest.mark.parametrize("region", ["Liège", "Flandre occidentale"])
    def test_a_province_is_slugified_for_both_belgian_portals(self, region):
        slug = Immoweb.slugify(region)
        assert slug in Immoweb().url_builder(RealEstateResearch(region=region), 1)
        assert slug in ImmoVlan().url_builder(RealEstateResearch(region=region), 1)

    def test_comparis_asks_for_a_canton_by_name(self):
        """comparis has one free-text location field; "Canton Vaud" is how
        its own canton pages fill it."""
        url = Comparis().url_builder(RealEstateResearch(region="Vaud"), 1)
        assert "Canton Vaud" in urllib.parse.unquote_plus(url)

    def test_a_bare_canton_name_would_mean_the_town_of_that_name(self):
        assert Comparis.location_of(RealEstateResearch(region="Vaud")) == "Canton Vaud"
        assert Comparis.location_of(RealEstateResearch(postal_code="1618")) == "1618"

    @pytest.mark.parametrize("worker_class", [Immoweb, ImmoVlan, Comparis])
    def test_the_region_wins_over_a_postal_code(self, worker_class):
        research = RealEstateResearch(postal_code="1400", region="Brabant wallon")
        url = urllib.parse.unquote(worker_class().url_builder(research, 1))
        assert "1400" not in url

    @pytest.mark.parametrize("worker_class", [Immoweb, ImmoVlan])
    def test_the_search_terms_still_apply_to_a_region(self, worker_class):
        url = worker_class().url_builder(
            RealEstateResearch(region="Namur", type=APARTMENT, rent_or_buy=RENT), 1
        )
        assert "appartement" in url and "a-louer" in url


class TestScanning:
    @pytest.fixture
    def country(self, monkeypatch):
        import ImmoScanner.ImmoScanner as module

        class Portal:
            domain_name = "portal.test"

            def __init__(self):
                self.researches = []

            def get_findings(self, research):
                self.researches.append(research)
                return []

        portal = Portal()
        looked_up = []

        class FakeCountry:
            REGIONS = ("Brabant wallon", "Namur")

            def get_real_estate_websites(self):
                return [portal]

            def find_region(self, name):
                return Belgium.find_region(self, name)

            def fetch_city_given_postal_code(self, code):
                looked_up.append(code)
                return "Nivelles"

            def fetch_postal_code_given_city(self, city):
                looked_up.append(city)
                return "1400"

        monkeypatch.setattr(
            module,
            "CountryFactory",
            lambda: type(
                "F",
                (),
                {"generate_country_given_name": lambda self, name: FakeCountry()},
            )(),
        )
        return portal, looked_up

    def test_a_region_reaches_the_portals(self, country):
        portal, _ = country
        ImmoScanner().research_real_estate("Belgium", region="brabant wallon")
        assert portal.researches[0].region == "Brabant wallon"

    def test_a_region_search_asks_geonames_nothing(self, country):
        """There is no single locality to resolve for a whole province."""
        portal, looked_up = country
        ImmoScanner().research_real_estate("Belgium", region="Namur")

        assert looked_up == []
        assert portal.researches[0].postal_code == ""
        assert portal.researches[0].city == ""

    def test_a_region_the_country_does_not_have_is_refused(self, country):
        with pytest.raises(ValueError, match="Atlantide"):
            ImmoScanner().research_real_estate("Belgium", region="Atlantide")

    def test_the_refusal_says_what_is_on_offer(self, country):
        with pytest.raises(ValueError, match="Brabant wallon"):
            ImmoScanner().research_real_estate("Belgium", region="Atlantide")

    def test_the_page_cap_can_be_raised_for_a_whole_region(self, country):
        portal, _ = country
        ImmoScanner().research_real_estate("Belgium", region="Namur", max_pages=60)
        assert portal.MAX_PAGES == 60


class TestNaming:
    def test_a_region_names_itself_in_the_archive(self, tmp_path):
        from ImmoScanner.Archives.Store import Store
        from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult

        item = RealEstateResearchResult()
        item.id, item.platform, item.price = "1", "immoweb.be", 300000
        item.livable_square_meters, item.city = 100, "Wavre"

        path = tmp_path / "a.db"
        with Store(path) as store:
            store.record("Belgium/Brabant wallon/any/buy", [item])

        with Explorer(path) as explorer:
            # not "Wavre": a province is not named after whichever town
            # happened to hold most of its listings
            assert explorer.searches()[0]["city"] == "Brabant wallon"
