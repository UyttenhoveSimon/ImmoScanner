"""Country lookups and the wiring from a country name to its portals."""

import pathlib

import pytest

from ImmoScanner.Countries.Belgium import Belgium
from ImmoScanner.Countries.Country import Country
from ImmoScanner.Countries.CountryFactory import CountryFactory
from ImmoScanner.Countries.Switzerland import Switzerland

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def geonames(monkeypatch):
    """Answer every geonames call with a captured page."""

    def serve(fixture_name):
        text = (FIXTURES / fixture_name).read_text() if fixture_name else ""
        calls = []

        def fake_get(url, params=None, headers=None, timeout=None):
            calls.append((url, params))
            return FakeResponse(text)

        monkeypatch.setattr("ImmoScanner.Countries.Country.requests.get", fake_get)
        return calls

    return serve


def belgium():
    country = Country()
    country.alpha_2 = "BE"
    return country


class TestGeonamesParsing:
    def test_reads_every_result_row(self, geonames):
        geonames("geonames_postal_5000.html")
        hits = belgium().search_postal_codes("5000")

        assert [hit["postal_code"] for hit in hits] == ["5000", "5000"]
        assert {hit["place"] for hit in hits} == {"Beez", "Namur"}

    def test_the_query_reaches_geonames(self, geonames):
        calls = geonames("geonames_postal_5000.html")
        belgium().search_postal_codes("5000")
        assert calls[0][1] == {"q": "5000", "country": "BE"}

    def test_a_page_without_a_result_table_yields_nothing(self, geonames):
        geonames(None)
        assert belgium().search_postal_codes("nowhere") == []


class TestPicking:
    def test_prefers_the_place_that_names_its_own_municipality(self, geonames):
        """5000 is both Beez and Namur; searches mean Namur."""
        geonames("geonames_postal_5000.html")
        assert belgium().fetch_city_given_postal_code("5000") == "Namur"

    def test_an_exact_name_match_wins(self):
        hits = [
            {"place": "Cognelée", "postal_code": "5022", "municipality": "Namur"},
            {"place": "Namur", "postal_code": "5000", "municipality": "Namur"},
        ]
        assert Country._pick(hits, preferred="Namur")["postal_code"] == "5000"

    def test_the_name_match_ignores_case(self):
        hits = [{"place": "Namur", "postal_code": "5000", "municipality": "X"}]
        assert Country._pick(hits, preferred="NAMUR")["postal_code"] == "5000"

    def test_the_first_hit_is_the_last_resort(self):
        hits = [
            {
                "place": "Châtel-St-Denis",
                "postal_code": "1618",
                "municipality": "Châtel-Saint-Denis",
            },
            {"place": "Elsewhere", "postal_code": "9999", "municipality": "Nowhere"},
        ]
        assert Country._pick(hits)["postal_code"] == "1618"

    def test_nothing_found_is_not_an_error(self):
        assert Country._pick([]) is None


class TestLookups:
    def test_a_city_is_found_for_a_postal_code(self, geonames):
        geonames("geonames_city_chatel.html")
        assert belgium().fetch_city_given_postal_code("1618") == "Châtel-St-Denis"

    def test_a_postal_code_is_found_for_a_city(self, geonames):
        geonames("geonames_city_chatel.html")
        assert belgium().fetch_postal_code_given_city("Châtel-St-Denis") == "1618"

    def test_only_hits_on_the_asked_postal_code_count(self, geonames):
        """geonames ranks by relevance, not by exact match."""
        geonames("geonames_postal_5000.html")
        assert belgium().fetch_city_given_postal_code("9999") == ""

    def test_an_unknown_city_gives_an_empty_answer(self, geonames):
        geonames(None)
        assert belgium().fetch_postal_code_given_city("Atlantis") == ""

    def test_a_city_name_is_escaped_before_it_is_sent(self, geonames):
        calls = geonames("geonames_city_chatel.html")
        belgium().fetch_postal_code_given_city("Braine-l'Alleud")
        assert " " not in calls[0][1]["q"]


class TestFactory:
    def test_belgium_is_built_with_its_iso_data(self):
        country = CountryFactory().generate_country_given_name("Belgium")

        assert (country.alpha_2, country.alpha_3, country.numeric) == (
            "BE",
            "BEL",
            "056",
        )
        assert country.official_name == "Kingdom of Belgium"

    def test_the_currency_is_not_derived_from_the_country_number(self):
        """ISO 3166 and ISO 4217 do not share a numbering: 056 is not EUR."""
        assert (
            CountryFactory().generate_country_given_name("Belgium").currency.alpha_3
            == "EUR"
        )
        assert (
            CountryFactory().generate_country_given_name("Switzerland").currency.alpha_3
            == "CHF"
        )

    def test_the_languages_are_not_derived_from_the_country_code(self):
        """ "be" is Belarusian and "ch" is Chamorro; neither is spoken there."""
        names = {
            language.name
            for language in CountryFactory()
            .generate_country_given_name("Belgium")
            .languages
        }
        assert names == {"Dutch", "French", "German"}
        assert "Belarusian" not in names

    def test_an_unknown_country_is_not_built(self):
        assert CountryFactory().generate_country_given_name("Atlantis") is None

    def test_each_call_builds_a_fresh_country(self):
        """Workers hold a browser session; two scans must not share one."""
        first = CountryFactory().generate_country_given_name("Belgium")
        second = CountryFactory().generate_country_given_name("Belgium")
        assert first is not second
        assert first.websites[0] is not second.websites[0]


class TestPortalRegistry:
    def test_belgium_serves_its_two_portals(self):
        assert {
            worker.domain_name for worker in Belgium().get_real_estate_websites()
        } == {
            "immoweb.be",
            "immovlan.be",
        }

    def test_switzerland_serves_comparis_only(self):
        """homegate and immoscout24 are behind DataDome; comparis carries both."""
        assert [
            worker.domain_name for worker in Switzerland().get_real_estate_websites()
        ] == ["comparis.ch"]

    def test_a_country_nobody_implemented_serves_no_portal(self):
        assert Country().get_real_estate_websites() == []

    @pytest.mark.parametrize("country_class", [Belgium, Switzerland])
    def test_a_country_declares_its_currency_and_languages(self, country_class):
        assert country_class.CURRENCY_CODE
        assert country_class.LANGUAGE_CODES
