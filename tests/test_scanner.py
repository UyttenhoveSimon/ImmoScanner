from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Intellectuals.StatisticalInsights import StatisticalInsights
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult
from ImmoScanner.Workers.RealEstateWorker import RealEstateWorker


def listing(price, area=100, bedrooms=3, postal="5000", platform="a", **extra):
    result = RealEstateResearchResult()
    result.platform = platform
    result.id = extra.pop("id", f"{platform}-{price}-{area}")
    result.price = price
    result.livable_square_meters = area
    result.bedrooms_number = bedrooms
    result.postal_code = postal
    for name, value in extra.items():
        setattr(result, name, value)
    return result


class TestDuplicateFinder:
    def test_drops_the_same_property_seen_on_two_portals(self):
        results = [[listing(300000, platform="a")], [listing(300000, platform="b")]]
        assert len(ImmoScanner().duplicate_finder(results)) == 1

    def test_keeps_two_genuinely_different_properties(self):
        results = [[listing(300000, area=100), listing(300000, area=140)]]
        assert len(ImmoScanner().duplicate_finder(results)) == 2

    def test_matches_on_position_when_the_measurements_differ(self):
        """Two portals rarely agree on a surface to the square metre."""
        results = [
            [listing(300000, area=100, latitude=50.4667, longitude=4.9152)],
            [listing(300000, area=101, latitude=50.4667, longitude=4.9152)],
        ]
        assert len(ImmoScanner().duplicate_finder(results)) == 1

    def test_ignores_listings_without_a_price_or_an_area(self):
        results = [[listing(0), listing(300000, area=0), listing(250000)]]
        assert len(ImmoScanner().duplicate_finder(results)) == 1

    def test_keeps_developments_even_though_they_have_no_price(self):
        project = listing(0, area=0, id="p1", is_project=True, price_min=230000)
        results = [[project, listing(250000)]]
        assert len(ImmoScanner().duplicate_finder(results)) == 2


class TestInsights:
    def test_reports_medians_and_gross_yield(self):
        selling = [listing(200000, area=100), listing(400000, area=100)]
        renting = [listing(1000, area=100, id="r1"), listing(2000, area=100, id="r2")]

        insights = ImmoScanner().get_insights(selling, renting)

        assert insights["selling_median_price"] == 300000
        assert insights["renting_median_price"] == 1500
        assert insights["gross_yield_percent"] == (1500 * 12) / 300000 * 100

    def test_leaves_developments_out_of_the_statistics(self):
        project = listing(0, area=0, id="p1", is_project=True, price_min=1_000_000)
        insights = ImmoScanner().get_insights([listing(200000), project])

        assert insights["listings"] == 1
        assert insights["projects"] == 1
        assert insights["selling_median_price"] == 200000

    def test_survives_an_empty_search(self):
        insights = ImmoScanner().get_insights([])
        assert insights["selling_median_price"] == 0

    def test_gross_yield_of_a_free_market_is_zero(self):
        assert StatisticalInsights.gross_yield(1000, 0) == 0


class TestHelpers:
    def test_replaces_an_existing_page_parameter(self):
        url = RealEstateWorker.with_query_param("https://x.be/s?a=1&page=1", "page", 4)
        assert "page=4" in url and "page=1" not in url and "a=1" in url

    def test_adds_a_page_parameter_when_there_is_none(self):
        assert RealEstateWorker.with_query_param("https://x.be/s", "page", 2).endswith(
            "page=2"
        )

    def test_first_int_ignores_thousand_separators(self):
        assert RealEstateWorker.first_int("129 MAISONS à vendre") == 129
        assert RealEstateWorker.first_int("1 020 000 €") == 1020000
        assert RealEstateWorker.first_int("pas de chiffre") == 0
