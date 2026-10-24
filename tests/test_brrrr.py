"""Ranking fixer-uppers against the postal code they stand in."""

import pytest

from ImmoScanner.Intellectuals import Brrrr
from ImmoScanner.Intellectuals.Renovation import RENOVATE, WORKS
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult

counter = iter(range(10_000))


def listing(price, surface=100, postal_code="4000", condition="", **extra):
    item = RealEstateResearchResult()
    item.id = str(next(counter))
    item.platform = "immoweb.be"
    item.price, item.livable_square_meters = price, surface
    item.postal_code, item.city = postal_code, extra.pop("city", "Liège")
    item.condition = condition
    for name, value in extra.items():
        setattr(item, name, value)
    return item


def renovated(price_per_m2, count=5, postal_code="4000"):
    return [listing(price_per_m2 * 100, postal_code=postal_code) for _ in range(count)]


class TestReference:
    def test_listings_needing_no_work_set_the_after_repair_value(self):
        wreck = listing(100_000, condition=RENOVATE)
        market = renovated(2_000) + [wreck, listing(50_000, condition=WORKS)]

        (opportunity,) = Brrrr.rank([wreck], market)

        assert opportunity.reference_scope == Brrrr.POSTAL_CODE
        assert opportunity.reference_price_per_m2 == 2_000
        assert opportunity.after_repair_value == 200_000
        assert opportunity.discount == pytest.approx(0.5)
        assert opportunity.notes == []

    def test_too_few_finished_comparables_fall_back_to_the_whole_postal_code(self):
        wreck = listing(100_000, condition=RENOVATE)
        market = renovated(2_000, count=2) + [
            listing(150_000, condition=WORKS) for _ in range(3)
        ]
        market.append(wreck)

        (opportunity,) = Brrrr.rank([wreck], market)

        assert opportunity.reference_scope == Brrrr.POSTAL_CODE_ALL
        assert opportunity.reference_price_per_m2 == 1_500
        assert opportunity.notes == ["reference: postal code, all"]

    def test_a_thin_postal_code_falls_back_to_the_scan(self):
        wreck = listing(100_000, postal_code="4020", condition=RENOVATE)
        market = renovated(2_400) + [wreck]

        (opportunity,) = Brrrr.rank([wreck], market)

        assert opportunity.reference_scope == Brrrr.SCAN
        assert opportunity.reference_price_per_m2 == 2_400

    def test_projects_and_listings_without_a_surface_are_skipped(self):
        project = listing(0, condition=RENOVATE, is_project=True)
        no_surface = listing(90_000, surface=0, condition=RENOVATE)
        assert Brrrr.rank([project, no_surface], renovated(2_000)) == []

    def test_nothing_to_compare_with_gives_nothing(self):
        assert Brrrr.rank([listing(100_000, condition=RENOVATE)], []) == []


class TestEconomics:
    def test_works_come_off_the_equity_and_onto_the_cost(self):
        wreck = listing(100_000, condition=RENOVATE)
        rentals = [listing(1_000) for _ in range(5)]  # 10/m² a month

        (opportunity,) = Brrrr.rank(
            [wreck], renovated(2_000) + [wreck], rentals, works_per_m2=500
        )

        assert opportunity.works_budget == 50_000
        assert opportunity.all_in_cost == 150_000
        assert opportunity.equity == 50_000
        assert opportunity.monthly_rent == 1_000
        assert opportunity.gross_yield_percent == pytest.approx(8.0)

    def test_without_rentals_there_is_no_rent(self):
        wreck = listing(100_000, condition=RENOVATE)
        (opportunity,) = Brrrr.rank([wreck], renovated(2_000))
        assert (opportunity.monthly_rent, opportunity.gross_yield_percent) == (0, 0)

    def test_thin_rentals_are_flagged(self):
        wreck = listing(100_000, condition=RENOVATE)
        (opportunity,) = Brrrr.rank([wreck], renovated(2_000), [listing(900)])
        assert opportunity.notes == ["rent: scan"]
        assert opportunity.monthly_rent == 900

    def test_the_best_discount_comes_first(self):
        cheap = listing(80_000, condition=RENOVATE)
        dear = listing(180_000, condition=RENOVATE)
        ranked = Brrrr.rank([dear, cheap], renovated(2_000))
        assert [o.item for o in ranked] == [cheap, dear]


class TestAreas:
    def test_one_row_per_postal_code(self):
        market = renovated(2_000) + [
            listing(120_000, postal_code="4020", city="Liège", condition=WORKS),
            listing(130_000, postal_code="4020", city="Liège"),
        ]
        rentals = [listing(1_000), listing(800, postal_code="4020")]

        rows = Brrrr.area_summary(market, rentals)

        assert [row["postal_code"] for row in rows] == ["4000", "4020"]
        assert rows[0]["median_price_per_m2"] == 2_000
        assert rows[0]["gross_yield_percent"] == pytest.approx(6.0)
        assert rows[1]["needing_work"] == 1
        assert rows[1]["median_rent_per_m2"] == 8

    def test_an_area_without_prices_has_no_yield(self):
        rows = Brrrr.area_summary([listing(0)])
        assert rows[0]["gross_yield_percent"] == 0
