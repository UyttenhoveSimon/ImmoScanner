"""The scan as a whole: locate, fan out, collect, survive a portal failing."""

import threading

import pytest

import ImmoScanner.ImmoScanner as scanner_module
from ImmoScanner.Console import split_list
from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Means.RealEstateResearch import (
    APARTMENT,
    BUY,
    HOUSE,
    RENT,
    RealEstateResearch,
)
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult
from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb


def result(listing_id, platform, price=300000, area=100):
    item = RealEstateResearchResult()
    item.id = listing_id
    item.platform = platform
    item.price = price
    item.livable_square_meters = area
    item.postal_code = "5000"
    return item


class SpyWorker:
    def __init__(self, domain_name, findings=(), error=None, barrier=None):
        self.domain_name = domain_name
        self.findings = list(findings)
        self.error = error
        self.barrier = barrier
        self.researches = []

    def get_findings(self, research):
        self.researches.append(research)
        if self.barrier is not None:
            # Only returns once every portal has reached this line, so the call
            # deadlocks and times out if the scan is running them one by one.
            self.barrier.wait(timeout=5)
        if self.error:
            raise self.error
        return self.findings


class FakeCountry:
    def __init__(self, workers, city="Namur", postal_code="5000"):
        self.workers = workers
        self.city = city
        self.postal_code = postal_code
        self.lookups = []

    def get_real_estate_websites(self):
        return self.workers

    def fetch_city_given_postal_code(self, postal_code):
        self.lookups.append(("city", postal_code))
        return self.city

    def fetch_postal_code_given_city(self, city):
        self.lookups.append(("postal", city))
        return self.postal_code


@pytest.fixture
def country(monkeypatch):
    """Install a fake country and hand it back for inspection."""
    holder = {}

    def install(workers, **kwargs):
        built = FakeCountry(workers, **kwargs)
        monkeypatch.setattr(
            scanner_module,
            "CountryFactory",
            lambda: type(
                "F", (), {"generate_country_given_name": lambda self, name: built}
            )(),
        )
        holder["country"] = built
        return built

    return install


class TestScan:
    def test_collects_one_group_per_portal(self, country):
        country(
            [
                SpyWorker("a.be", [result("1", "a.be")]),
                SpyWorker("b.be", [result("2", "b.be"), result("3", "b.be")]),
            ]
        )
        results = ImmoScanner().research_real_estate("Belgium", postal_code="5000")
        assert [len(group) for group in results] == [1, 2]

    def test_each_portal_gets_its_own_research_object(self, country):
        """fill_empty_fields mutates it; a shared one would leak between portals."""
        workers = [SpyWorker("a.be"), SpyWorker("b.be")]
        country(workers)
        ImmoScanner().research_real_estate("Belgium", postal_code="5000")

        first, second = workers[0].researches[0], workers[1].researches[0]
        assert first is not second
        assert first.postal_code == second.postal_code == "5000"

    def test_portals_are_scanned_side_by_side(self, country):
        barrier = threading.Barrier(3)
        workers = [SpyWorker(f"{n}.be", barrier=barrier) for n in "abc"]
        country(workers)

        ImmoScanner().research_real_estate("Belgium", postal_code="5000")

        assert not barrier.broken  # nobody timed out waiting for the others

    def test_one_portal_failing_does_not_lose_the_others(self, country):
        country(
            [
                SpyWorker("broken.be", error=RuntimeError("blocked")),
                SpyWorker("fine.be", [result("1", "fine.be")]),
            ]
        )
        results = ImmoScanner().research_real_estate("Belgium", postal_code="5000")
        assert [len(group) for group in results] == [0, 1]

    def test_the_missing_half_of_the_location_is_looked_up(self, country):
        built = country([SpyWorker("a.be")])
        ImmoScanner().research_real_estate("Belgium", city="Namur")
        assert built.lookups == [("postal", "Namur")]

        built.lookups.clear()
        ImmoScanner().research_real_estate("Belgium", postal_code="5000")
        assert built.lookups == [("city", "5000")]

    def test_the_search_terms_reach_the_portal(self, country):
        worker = SpyWorker("a.be")
        country([worker])
        ImmoScanner().research_real_estate(
            "Belgium", postal_code="5000", type=APARTMENT, rent_or_buy=RENT
        )
        assert worker.researches[0].type == APARTMENT
        assert worker.researches[0].rent_or_buy == RENT

    def test_an_unknown_country_is_refused(self, monkeypatch):
        monkeypatch.setattr(
            scanner_module,
            "CountryFactory",
            lambda: type(
                "F", (), {"generate_country_given_name": lambda self, name: None}
            )(),
        )
        with pytest.raises(ValueError):
            ImmoScanner().research_real_estate("Atlantis", postal_code="1")

    def test_a_country_with_no_portal_left_is_refused(self, country):
        country([])
        with pytest.raises(ValueError):
            ImmoScanner().research_real_estate("Belgium", postal_code="5000")


class TestUrlMode:
    def test_only_the_portal_owning_the_domain_is_asked(self, country):
        immoweb, immovlan = SpyWorker(
            "immoweb.be", [result("1", "immoweb.be")]
        ), SpyWorker("immovlan.be")
        country([immoweb, immovlan])

        results = ImmoScanner().research_real_estate_url(
            "Belgium", "https://www.immoweb.be/fr/recherche/maison/a-vendre/namur/5000"
        )
        assert [len(group) for group in results] == [1]
        assert immovlan.researches == []

    def test_an_unknown_domain_yields_nothing(self, country):
        country([SpyWorker("immoweb.be")])
        assert (
            ImmoScanner().research_real_estate_url("Belgium", "https://example.com/x")
            == []
        )


class TestSearchUrls:
    """Regression cover for the locality bugs, which went both ways.

    "Braine-L'Alleud" in an immoweb path returned a generic page with no
    listing at all, so immoweb searches on the postal code alone. immovlan
    needs the name as well: a postal code covering several localities resolves
    to whichever one it feels like - 1400 alone means Monstreux and its two
    listings, not Nivelles and its hundred.
    """

    def test_immoweb_leaves_the_city_name_out_entirely(self):
        research = RealEstateResearch(postal_code="1420", city="Braine-L'Alleud")
        url = Immoweb().url_builder(research, 1)
        assert "postalCodes=1420" in url
        assert "raine" not in url and "'" not in url

    def test_immoweb_paginates_on_the_query(self):
        url = Immoweb().url_builder(RealEstateResearch(postal_code="1420"), 2)
        assert "postalCodes=1420" in url and "page=2" in url

    def test_immovlan_pairs_the_postal_code_with_the_town(self):
        url = ImmoVlan().url_builder(
            RealEstateResearch(postal_code="1400", city="Nivelles"), 1
        )
        assert "towns=1400-nivelles" in url

    @pytest.mark.parametrize(
        "city, slug",
        [
            ("Braine-L'Alleud", "braine-l-alleud"),
            ("Liège", "liege"),
            ("Ottignies-Louvain-la-Neuve", "ottignies-louvain-la-neuve"),
        ],
    )
    def test_immovlan_slugifies_the_town(self, city, slug):
        """An unrecognised spelling makes immovlan answer with the country."""
        url = ImmoVlan().url_builder(
            RealEstateResearch(postal_code="1420", city=city), 1
        )
        assert f"towns=1420-{slug}" in url

    def test_immovlan_falls_back_to_the_code_when_the_town_is_unknown(self):
        url = ImmoVlan().url_builder(RealEstateResearch(postal_code="1400"), 1)
        assert "towns=1400&" in url

    @pytest.mark.parametrize(
        "worker_class, expected",
        [(Immoweb, ("maison", "appartement")), (ImmoVlan, ("maison", "appartement"))],
    )
    def test_the_property_type_is_translated_per_portal(self, worker_class, expected):
        house = worker_class().url_builder(
            RealEstateResearch(postal_code="1420", type=HOUSE), 1
        )
        flat = worker_class().url_builder(
            RealEstateResearch(postal_code="1420", type=APARTMENT), 1
        )
        assert expected[0] in house and expected[1] in flat

    @pytest.mark.parametrize("worker_class", [Immoweb, ImmoVlan])
    def test_renting_and_buying_are_different_searches(self, worker_class):
        buy = worker_class().url_builder(
            RealEstateResearch(postal_code="1420", rent_or_buy=BUY), 1
        )
        rent = worker_class().url_builder(
            RealEstateResearch(postal_code="1420", rent_or_buy=RENT), 1
        )
        assert buy != rent
        assert "a-vendre" in buy and "a-louer" in rent

    def test_comparis_pages_are_zero_based(self):
        assert "page=0" in Comparis().url_builder(
            RealEstateResearch(postal_code="1618"), 1
        )
        assert "page=1" in Comparis().url_builder(
            RealEstateResearch(postal_code="1618"), 2
        )

    def test_comparis_asks_for_the_right_deal_type(self):
        buy = Comparis().url_builder(
            RealEstateResearch(postal_code="1618", rent_or_buy=BUY), 1
        )
        rent = Comparis().url_builder(
            RealEstateResearch(postal_code="1618", rent_or_buy=RENT), 1
        )
        assert "DealType%22%3A20" in buy and "DealType%22%3A10" in rent

    @pytest.mark.parametrize("worker_class", [Immoweb, ImmoVlan, Comparis])
    def test_a_supplied_url_is_paginated_not_repeated(self, worker_class):
        research = RealEstateResearch(url="https://portal.test/search?q=1&page=1")
        pages = {worker_class().url_builder(research, n) for n in (1, 2, 3)}
        assert len(pages) == 3
        assert all("q=1" in url for url in pages)


class TestConsoleHelpers:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("", []),
            ("homegate", ["homegate"]),
            ("homegate,immoscout24", ["homegate", "immoscout24"]),
            (" homegate , immoscout24 ", ["homegate", "immoscout24"]),
            ("homegate,,", ["homegate"]),
        ],
    )
    def test_comma_separated_options(self, raw, expected):
        assert split_list(raw) == expected
