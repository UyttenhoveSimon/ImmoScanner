import sqlite3

from ImmoScanner.Archives.Store import Store
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult

SEARCH = "Belgium/5000/house/buy"


def listing(listing_id, price, platform="immoweb.be"):
    result = RealEstateResearchResult()
    result.platform = platform
    result.id = listing_id
    result.price = price
    result.url = f"https://x.be/{listing_id}"
    result.city = "Namur"
    result.postal_code = "5000"
    result.livable_square_meters = 120
    return result


def test_a_first_run_is_all_new(tmp_path):
    with Store(tmp_path / "a.db") as store:
        report = store.record(SEARCH, [listing("1", 300000), listing("2", 400000)])

    assert len(report.new) == 2
    assert report.unchanged == 0


def test_an_unchanged_run_reports_nothing(tmp_path):
    with Store(tmp_path / "a.db") as store:
        store.record(SEARCH, [listing("1", 300000)])
        report = store.record(SEARCH, [listing("1", 300000)])

    assert report.new == [] and report.price_changes == [] and report.unchanged == 1


def test_a_price_cut_is_reported_with_its_previous_value(tmp_path):
    with Store(tmp_path / "a.db") as store:
        store.record(SEARCH, [listing("1", 300000)])
        report = store.record(SEARCH, [listing("1", 275000)])

        assert [(item.id, previous) for item, previous in report.price_changes] == [
            ("1", 300000.0)
        ]
        assert [row["price"] for row in store.price_history("immoweb.be", "1")] == [
            300000.0,
            275000.0,
        ]


def test_a_listing_the_search_no_longer_reaches_is_gone(tmp_path):
    with Store(tmp_path / "a.db") as store:
        store.record(SEARCH, [listing("1", 300000), listing("2", 400000)])
        report = store.record(SEARCH, [listing("1", 300000)])

    assert [row["listing_id"] for row in report.gone] == ["2"]


def test_another_search_is_not_treated_as_a_withdrawal(tmp_path):
    with Store(tmp_path / "a.db") as store:
        store.record(SEARCH, [listing("1", 300000)])
        report = store.record("Belgium/1000/house/buy", [listing("9", 500000)])

    assert report.gone == []


def test_the_plot_is_archived(tmp_path):
    result = listing("1", 300000)
    result.land_square_meters = 800
    with Store(tmp_path / "a.db") as store:
        store.record(SEARCH, [result])
        row = store.connection.execute(
            "SELECT land_square_meters FROM listings"
        ).fetchone()
    assert row[0] == 800


def test_an_archive_from_before_plots_were_kept_is_brought_up_to_date(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as old:
        old.execute(
            "CREATE TABLE listings (platform TEXT NOT NULL, listing_id TEXT NOT NULL, "
            "search_key TEXT NOT NULL, url TEXT, description TEXT, type TEXT, "
            "source TEXT, postal_code TEXT, city TEXT, currency TEXT, price REAL, "
            "livable_square_meters INTEGER, bedrooms_number INTEGER, rooms_number REAL, "
            "latitude REAL, longitude REAL, first_seen TEXT NOT NULL, "
            "last_seen TEXT NOT NULL, PRIMARY KEY (platform, listing_id))"
        )
    with Store(path) as store:
        report = store.record(SEARCH, [listing("1", 300000)])
    assert len(report.new) == 1
