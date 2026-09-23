"""Coordinates: where they come from, and what they are used for.

Only some portals geocode their listings, and the ones that do are the reason
de-duplication can tell two advertisements for one building apart from two
genuinely different flats. These tests pin both the parsing and the matching.
"""

import pytest

from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Means.RealEstateResearchResult import (
    COORDINATE_PRECISION,
    RealEstateResearchResult,
)
from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb

# Belgium spans roughly 49.5-51.5 N, 2.5-6.4 E; Switzerland 45.8-47.8 N, 5.9-10.5 E
BELGIUM = ((49.4, 51.6), (2.4, 6.5))
SWITZERLAND = ((45.7, 47.9), (5.8, 10.6))


def at(latitude, longitude, price=300000, area=100, **extra):
    result = RealEstateResearchResult()
    result.platform = extra.pop("platform", "a")
    result.id = extra.pop("id", f"{latitude}-{longitude}-{price}")
    result.price = price
    result.livable_square_meters = area
    result.postal_code = extra.pop("postal_code", "5000")
    result.latitude = latitude
    result.longitude = longitude
    for name, value in extra.items():
        setattr(result, name, value)
    return result


def within(result, box):
    (south, north), (west, east) = box
    return south < result.latitude < north and west < result.longitude < east


class TestFingerprint:
    def test_a_listing_without_coordinates_has_no_geographic_key(self):
        assert at(None, None).geo_fingerprint() is None
        assert at(50.4, None).geo_fingerprint() is None
        assert at(None, 4.8).geo_fingerprint() is None

    def test_the_coarse_key_still_works_without_coordinates(self):
        assert at(None, None).fingerprint() == ("5000", 300000, 100, 0)

    def test_neighbouring_points_collapse_onto_one_cell(self):
        """Two portals geocoding one address land a few metres apart."""
        assert (
            at(50.46669, 4.91516).geo_fingerprint()
            == at(50.466692, 4.915163).geo_fingerprint()
        )

    def test_points_further_apart_stay_distinct(self):
        # a thousandth of a degree is about 110 m
        assert (
            at(50.4667, 4.9152).geo_fingerprint()
            != at(50.4677, 4.9152).geo_fingerprint()
        )

    def test_the_price_is_part_of_the_key(self):
        assert (
            at(50.4667, 4.9152, price=300000).geo_fingerprint()
            != at(50.4667, 4.9152, price=310000).geo_fingerprint()
        )

    def test_the_cell_is_about_ten_metres(self):
        assert COORDINATE_PRECISION == 4


class TestDeduplication:
    def test_one_building_two_portals_one_property(self):
        listings = [
            [at(50.4667, 4.9152, area=100, platform="immoweb.be")],
            [at(50.46671, 4.91521, area=101, platform="immovlan.be")],
        ]
        assert len(ImmoScanner().duplicate_finder(listings)) == 1

    def test_two_flats_in_one_building_at_different_prices_both_survive(self):
        listings = [
            [
                at(50.4667, 4.9152, price=300000, area=80, id="a"),
                at(50.4667, 4.9152, price=420000, area=120, id="b"),
            ]
        ]
        assert len(ImmoScanner().duplicate_finder(listings)) == 2

    def test_identical_flats_in_one_building_are_merged(self):
        """A known and accepted loss.

        Two flats at the same address, same price and same surface are
        indistinguishable from one listing published twice, and the duplicate
        is by far the commoner case.
        """
        listings = [
            [
                at(50.4667, 4.9152, price=300000, area=80, id="a"),
                at(50.4667, 4.9152, price=300000, area=80, id="b"),
            ]
        ]
        assert len(ImmoScanner().duplicate_finder(listings)) == 1

    def test_a_portal_without_coordinates_still_de_duplicates(self):
        listings = [
            [at(None, None, price=300000, area=100, platform="immovlan.be")],
            [at(None, None, price=300000, area=100, platform="immoweb.be")],
        ]
        assert len(ImmoScanner().duplicate_finder(listings)) == 1

    def test_a_geocoded_listing_matches_one_without_coordinates(self):
        """The coarse key is the common denominator; neither portal is lost."""
        listings = [
            [at(50.4667, 4.9152, price=300000, area=100, platform="immoweb.be")],
            [at(None, None, price=300000, area=100, platform="immovlan.be")],
        ]
        assert len(ImmoScanner().duplicate_finder(listings)) == 1


class TestParsing:
    def test_immoweb_reads_coordinates_out_of_the_embedded_json(self, soup_of):
        worker = Immoweb()
        cards = soup_of("immoweb_search.html").select(worker.CARD_SELECTOR)
        located = [
            result
            for result in (worker.extract_findings(card) for card in cards)
            if result.latitude is not None
        ]
        assert located
        assert all(within(result, BELGIUM) for result in located)

    def test_comparis_reads_the_coordinate_object(self, soup_of):
        worker = Comparis()
        data = worker.parse_result_data(soup_of("comparis_search.html"), "fixture")
        results = [worker.extract_findings(item) for item in data["resultItems"]]

        assert all(result.latitude and result.longitude for result in results)
        assert all(within(result, SWITZERLAND) for result in results)

    def test_immovlan_publishes_no_position(self, soup_of):
        """Documented gap: its cards carry a locality, never a point."""
        worker = ImmoVlan()
        cards = soup_of("immovlan_search.html").select(worker.CARD_SELECTOR)
        results = [worker.extract_findings(card) for card in cards]

        assert results
        assert all(result.latitude is None for result in results)
        assert all(result.geo_fingerprint() is None for result in results)
        assert all(result.postal_code for result in results)

    @pytest.mark.parametrize("missing", ["Latitude", "Longitude"])
    def test_comparis_survives_a_half_filled_coordinate(self, missing):
        worker = Comparis()
        item = {
            "AdId": 1,
            "Price": "1",
            "PriceValue": 1,
            "Currency": "CHF",
            "Address": ["1618 Châtel-St-Denis"],
            "Coordinate": {"Latitude": 46.5, "Longitude": 6.9},
        }
        item["Coordinate"].pop(missing)
        assert worker.extract_findings(item).geo_fingerprint() is None
