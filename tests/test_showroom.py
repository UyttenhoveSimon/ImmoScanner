"""The explorer: the questions it answers, and the server that exposes them."""

import json
import sqlite3
import threading
import urllib.request

import pytest

import ImmoScanner.Showrooms.Server as server_module
from ImmoScanner.Archives.Store import Store
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult
from ImmoScanner.Showrooms.Explorer import MAX_LIMIT, Explorer, bounded, quantile
from ImmoScanner.Showrooms.Server import PAGE, answer, build_server, serve

NAMUR = "Belgium/5000/any/buy"
WATERLOO = "Belgium/1410/any/buy"


def listing(
    listing_id, price, area=100, platform="immoweb.be", source="", city="Namur"
):
    item = RealEstateResearchResult()
    item.id, item.platform, item.source = listing_id, platform, source
    item.price, item.livable_square_meters = price, area
    item.city, item.postal_code = city, "5000"
    item.url = f"https://{platform}/{listing_id}"
    item.description = f"listing {listing_id}"
    return item


@pytest.fixture
def archive(tmp_path):
    """An archive holding two searches, one of which has moved in price."""
    path = tmp_path / "archive.db"
    with Store(path) as store:
        store.record(
            NAMUR,
            [
                listing("1", 200000),
                listing("2", 400000, 200),
                listing("3", 300000, source="partner.be"),
            ],
        )
        store.record(WATERLOO, [listing("9", 600000, 120, city="Waterloo")])
        store.record(
            NAMUR,
            [
                listing("1", 180000),
                listing("2", 400000, 200),
                listing("3", 300000, source="partner.be"),
            ],
        )
    return path


class TestSearches:
    def test_every_archived_search_is_listed(self, archive):
        with Explorer(archive) as explorer:
            assert [row["search_key"] for row in explorer.searches()] == [
                WATERLOO,
                NAMUR,
            ]

    def test_each_search_carries_what_compares_it(self, archive):
        with Explorer(archive) as explorer:
            namur = next(s for s in explorer.searches() if s["search_key"] == NAMUR)

        assert namur["listings"] == 3
        assert namur["median_price"] == 300000
        assert namur["median_price_per_m2"] == 2000  # 180k/100, 300k/100, 400k/200
        assert (
            namur["first_quartile"] <= namur["median_price"] <= namur["third_quartile"]
        )

    def test_a_search_with_no_price_does_not_break_the_statistics(self, tmp_path):
        path = tmp_path / "a.db"
        with Store(path) as store:
            store.record("scope", [listing("1", 0)])
        with Explorer(path) as explorer:
            assert explorer.searches()[0]["median_price"] == 0

    def test_an_empty_archive_compares_nothing(self, tmp_path):
        path = tmp_path / "a.db"
        Store(path).close()
        with Explorer(path) as explorer:
            assert explorer.searches() == []


class TestListings:
    def test_a_search_narrows_the_rows(self, archive):
        with Explorer(archive) as explorer:
            assert len(explorer.listings(search_key=WATERLOO)) == 1
            assert len(explorer.listings()) == 4

    def test_the_originating_portal_can_be_filtered_on(self, archive):
        with Explorer(archive) as explorer:
            rows = explorer.listings(source="partner")
        assert [row["listing_id"] for row in rows] == ["3"]

    def test_the_sort_is_a_whitelist_not_a_fragment_of_sql(self, archive):
        """Whatever the browser sends, it never reaches sqlite as sql."""
        with Explorer(archive) as explorer:
            rows = explorer.listings(sort="price; DROP TABLE listings")
            assert rows  # fell back to the default ordering
            assert explorer.listings(search_key=NAMUR)  # the table is still there

    def test_sorting_by_price_per_square_metre(self, archive):
        with Explorer(archive) as explorer:
            rows = explorer.listings(search_key=NAMUR, sort="price_per_m2")
        ratios = [row["price"] / row["livable_square_meters"] for row in rows]
        assert ratios == sorted(ratios, reverse=True)

    def test_priceless_listings_are_pushed_to_the_bottom(self, tmp_path):
        path = tmp_path / "a.db"
        with Store(path) as store:
            store.record("scope", [listing("empty", 0), listing("priced", 100000)])
        with Explorer(path) as explorer:
            assert [row["listing_id"] for row in explorer.listings()] == [
                "priced",
                "empty",
            ]

    def test_the_row_count_is_bounded(self, archive):
        with Explorer(archive) as explorer:
            assert len(explorer.listings(limit=1)) == 1


class TestHistoryAndMovements:
    def test_every_price_a_listing_has_shown_is_kept(self, archive):
        with Explorer(archive) as explorer:
            history = explorer.price_history("immoweb.be", "1")
        assert [point["price"] for point in history] == [200000, 180000]

    def test_only_listings_whose_price_moved_are_reported(self, archive):
        with Explorer(archive) as explorer:
            moved = explorer.movements(NAMUR)
        assert [row["listing_id"] for row in moved] == ["1"]
        assert moved[0]["first_price"] == 200000
        assert moved[0]["price"] == 180000

    def test_the_deepest_cut_comes_first(self, tmp_path):
        path = tmp_path / "a.db"
        with Store(path) as store:
            store.record("scope", [listing("small", 300000), listing("big", 500000)])
            store.record("scope", [listing("small", 290000), listing("big", 400000)])
        with Explorer(path) as explorer:
            assert [row["listing_id"] for row in explorer.movements("scope")] == [
                "big",
                "small",
            ]


class TestHelpers:
    @pytest.mark.parametrize(
        "given, expected",
        [(None, 200), ("", 200), ("abc", 200), (0, 1), (5, 5), (99999, MAX_LIMIT)],
    )
    def test_a_limit_is_always_sane(self, given, expected):
        assert bounded(given) == expected

    def test_a_quantile_of_nothing_is_zero(self):
        assert quantile([], 0.5) == 0

    def test_a_quantile_picks_a_value_that_is_in_the_set(self):
        values = [1, 2, 3, 4]
        assert quantile(values, 0.25) in values
        assert quantile(values, 1.0) == 4


class TestReadOnly:
    def test_the_explorer_cannot_write_to_the_archive(self, archive):
        with Explorer(archive) as explorer:
            with pytest.raises(sqlite3.OperationalError):
                explorer.connection.execute("DELETE FROM listings")


class TestRouting:
    def test_each_api_path_reaches_its_view(self, archive):
        with Explorer(archive) as explorer:
            assert answer(explorer, "/api/searches", {})
            assert answer(explorer, "/api/listings", {"search": NAMUR})
            assert answer(
                explorer, "/api/history", {"platform": "immoweb.be", "id": "1"}
            )
            assert answer(explorer, "/api/movements", {"search": NAMUR})

    def test_an_unknown_path_has_no_view(self, archive):
        with Explorer(archive) as explorer:
            assert answer(explorer, "/api/whatever", {}) is None


@pytest.fixture
def running(archive):
    server = build_server(archive, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def fetch(base, path):
    with urllib.request.urlopen(base + path) as response:
        return response.status, response.read()


class TestServer:
    def test_the_page_is_served_at_the_root(self, running):
        status, body = fetch(running, "/")
        assert status == 200
        assert b"ImmoScanner" in body and len(body) == PAGE.stat().st_size

    def test_the_api_answers_json(self, running):
        status, body = fetch(running, "/api/searches")
        assert status == 200
        assert {row["search_key"] for row in json.loads(body)} == {NAMUR, WATERLOO}

    def test_query_parameters_reach_the_explorer(self, running):
        _, body = fetch(running, f"/api/listings?search={WATERLOO.replace('/', '%2F')}")
        assert [row["city"] for row in json.loads(body)] == ["Waterloo"]

    def test_an_empty_parameter_is_treated_as_absent(self, running):
        _, body = fetch(running, "/api/listings?source=&limit=")
        assert len(json.loads(body)) == 4

    @pytest.mark.parametrize("path", ["/nope", "/api/nope", "/../etc/passwd"])
    def test_anything_that_is_not_a_view_is_refused(self, running, path):
        with pytest.raises(urllib.error.HTTPError) as refused:
            fetch(running, path)
        assert refused.value.code == 404

    def test_a_question_the_archive_cannot_answer_is_a_server_error(
        self, running, archive
    ):
        archive.unlink()
        with pytest.raises(urllib.error.HTTPError) as failed:
            fetch(running, "/api/searches")
        assert failed.value.code == 500

    def test_it_listens_on_the_loopback_only(self, archive):
        server = build_server(archive, port=0)
        try:
            assert server.server_address[0] == "127.0.0.1"
        finally:
            server.server_close()


class FakeServer:
    def __init__(self, interrupt=True):
        self.server_address = ("127.0.0.1", 8765)
        self.interrupt = interrupt
        self.served = False
        self.shut_down = False
        self.closed = False

    def serve_forever(self):
        self.served = True
        if self.interrupt:
            raise KeyboardInterrupt

    def shutdown(self):
        self.shut_down = True

    def server_close(self):
        self.closed = True


class TestServeCommand:
    def test_there_is_nothing_to_explore_without_an_archive(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="--store"):
            serve(tmp_path / "absent.db")

    def test_the_address_is_announced_before_it_blocks(
        self, archive, monkeypatch, capsys
    ):
        built = FakeServer()
        monkeypatch.setattr(server_module, "build_server", lambda *a, **k: built)

        serve(archive)

        assert built.served
        assert "http://127.0.0.1:8765" in capsys.readouterr().out

    def test_the_socket_is_released_on_the_way_out(self, archive, monkeypatch):
        built = FakeServer()
        monkeypatch.setattr(server_module, "build_server", lambda *a, **k: built)

        serve(archive)

        assert built.shut_down and built.closed

    def test_a_server_that_stops_on_its_own_is_cleaned_up_too(
        self, archive, monkeypatch
    ):
        built = FakeServer(interrupt=False)
        monkeypatch.setattr(server_module, "build_server", lambda *a, **k: built)

        serve(archive)

        assert built.shut_down and built.closed
