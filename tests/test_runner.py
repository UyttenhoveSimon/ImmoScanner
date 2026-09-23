"""Scans asked for from the page: what is accepted, and what comes back."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult
from ImmoScanner.Showrooms.Runner import DONE, FAILED, IDLE, RUNNING, Busy, ScanRunner
from ImmoScanner.Showrooms.Server import build_server


def listing(listing_id="1", price=300000):
    item = RealEstateResearchResult()
    item.id, item.platform, item.price = listing_id, "immoweb.be", price
    item.livable_square_meters = 100
    return item


class FakeScanner:
    def __init__(self, findings=None, error=None, gate=None):
        self.findings = findings if findings is not None else [listing()]
        self.error = error
        self.gate = gate
        self.asked = []

    def research_real_estate(self, **kwargs):
        self.asked.append(kwargs)
        if self.gate is not None:
            self.gate.wait(timeout=5)
        if self.error:
            raise self.error
        return [self.findings]

    def duplicate_finder(self, results):
        return [item for group in results for item in group]


class FakeReport:
    def summary(self):
        return "1 new, 0 repriced, 0 gone, 0 unchanged"


class FakeStore:
    """Stands in for the archive; records what it was asked to keep."""

    recorded = []

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @staticmethod
    def search_key(country, place, type, rent_or_buy):
        return f"{country}/{place}/{type}/{rent_or_buy}"

    def record(self, key, findings):
        FakeStore.recorded.append((key, list(findings)))
        return FakeReport()


@pytest.fixture(autouse=True)
def clean():
    FakeStore.recorded = []


def runner(scanner=None, **kwargs):
    return ScanRunner(
        "archive.db", scanner=scanner or FakeScanner(), store=FakeStore, **kwargs
    )


def finished(runner):
    runner.thread.join(timeout=5)
    return runner.status()


class TestValidation:
    def test_a_scan_needs_somewhere_to_look(self):
        with pytest.raises(ValueError, match="postal code"):
            runner().start("Belgium")

    def test_a_region_is_somewhere_to_look(self):
        assert (
            runner().start("Belgium", region="Brabant wallon")["asked"]
            == "Brabant wallon"
        )

    def test_an_unknown_property_type_is_refused(self):
        with pytest.raises(ValueError, match="castle"):
            runner().start("Belgium", postal_code="1300", type="castle")

    def test_an_unknown_transaction_is_refused(self):
        with pytest.raises(ValueError, match="swap"):
            runner().start("Belgium", postal_code="1300", rent_or_buy="swap")

    def test_a_city_is_enough(self):
        assert runner().start("Belgium", city="Wavre")["state"] == RUNNING


class TestRunning:
    def test_nothing_is_running_to_begin_with(self):
        assert runner().status() == {"state": IDLE}

    def test_the_scan_reaches_the_scanner_as_asked(self):
        scanner = FakeScanner()
        started = runner(scanner)
        started.start(
            "Belgium", postal_code="1300", type="apartment", rent_or_buy="rent"
        )
        finished(started)

        assert scanner.asked == [
            {
                "country_name": "Belgium",
                "postal_code": "1300",
                "city": "",
                "region": "",
                "type": "apartment",
                "rent_or_buy": "rent",
            }
        ]

    def test_what_was_found_is_archived_under_the_search(self):
        started = runner()
        started.start("Belgium", postal_code="1300")
        finished(started)

        key, findings = FakeStore.recorded[0]
        assert key == "Belgium/1300/any/buy"
        assert len(findings) == 1

    def test_the_finished_state_says_what_came_of_it(self):
        started = runner()
        started.start("Belgium", postal_code="1300")
        state = finished(started)

        assert state["state"] == DONE
        assert state["search_key"] == "Belgium/1300/any/buy"
        assert state["scanned"] == 1 and state["listings"] == 1
        assert "1 new" in state["summary"]

    def test_a_scan_that_blows_up_is_reported_not_swallowed(self):
        started = runner(FakeScanner(error=RuntimeError("the portal is down")))
        started.start("Belgium", postal_code="1300")
        state = finished(started)

        assert state["state"] == FAILED
        assert "the portal is down" in state["error"]

    def test_the_answer_survives_a_scan_finding_nothing(self):
        started = runner(FakeScanner(findings=[]))
        started.start("Belgium", postal_code="1300")
        assert finished(started)["listings"] == 0


class TestOneAtATime:
    def test_a_second_scan_is_refused_while_one_is_under_way(self):
        gate = threading.Barrier(2)
        started = runner(FakeScanner(gate=gate))
        started.start("Belgium", postal_code="1300")

        try:
            with pytest.raises(Busy, match="1300"):
                started.start("Belgium", postal_code="1400")
        finally:
            gate.wait(timeout=5)
            finished(started)

    def test_another_scan_is_welcome_once_the_first_is_done(self):
        started = runner()
        started.start("Belgium", postal_code="1300")
        finished(started)

        assert started.start("Belgium", postal_code="1400")["state"] == RUNNING
        finished(started)
        assert [key for key, _ in FakeStore.recorded] == [
            "Belgium/1300/any/buy",
            "Belgium/1400/any/buy",
        ]


@pytest.fixture
def running(tmp_path):
    from ImmoScanner.Archives.Store import Store

    archive = tmp_path / "a.db"
    Store(archive).close()

    scans = runner()
    server = build_server(archive, host="127.0.0.1", port=0, runner=scans)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", scans
    server.shutdown()
    server.server_close()


def post(base, payload, raw=None):
    request = urllib.request.Request(
        base + "/api/scans",
        data=raw if raw is not None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read())


class TestScanEndpoint:
    def test_the_page_is_told_what_it_may_ask_for(self, running):
        base, _ = running
        with urllib.request.urlopen(base + "/api/options") as response:
            options = json.loads(response.read())

        assert "Belgium" in options["countries"]
        assert options["types"][0] == "any"
        assert set(options["transactions"]) == {"buy", "rent"}

    def test_asking_for_a_scan_is_accepted_and_not_waited_on(self, running):
        base, scans = running
        status, body = post(base, {"country": "Belgium", "postal_code": "1300"})

        assert status == 202
        assert body["state"] == RUNNING
        finished(scans)

    def test_the_page_can_poll_for_where_it_got_to(self, running):
        base, scans = running
        post(base, {"country": "Belgium", "postal_code": "1300"})
        finished(scans)

        with urllib.request.urlopen(base + "/api/scans") as response:
            assert json.loads(response.read())["state"] == DONE

    def test_a_second_ask_while_busy_is_a_conflict(self, running):
        base, scans = running
        scans.scanner.gate = threading.Barrier(2)
        post(base, {"country": "Belgium", "postal_code": "1300"})

        try:
            with pytest.raises(urllib.error.HTTPError) as refused:
                post(base, {"country": "Belgium", "postal_code": "1400"})
            assert refused.value.code == 409
        finally:
            scans.scanner.gate.wait(timeout=5)
            finished(scans)

    @pytest.mark.parametrize(
        "payload",
        [
            {"country": "Belgium"},
            {"country": "Belgium", "postal_code": "1", "type": "castle"},
        ],
    )
    def test_an_impossible_ask_is_refused(self, running, payload):
        base, _ = running
        with pytest.raises(urllib.error.HTTPError) as refused:
            post(base, payload)
        assert refused.value.code == 400

    @pytest.mark.parametrize(
        "place, expected",
        [
            ("1400", {"postal_code": "1400", "city": ""}),
            ("Nivelles", {"postal_code": "", "city": "Nivelles"}),
        ],
    )
    def test_one_field_on_the_page_becomes_a_code_or_a_name(
        self, running, place, expected
    ):
        """Typing a postal code is not friendly; the page asks for either."""
        base, scans = running
        post(base, {"country": "Belgium", "place": place})
        finished(scans)

        asked = scans.scanner.asked[0]
        assert asked["postal_code"] == expected["postal_code"]
        assert asked["city"] == expected["city"]

    def test_a_body_that_is_not_json_is_refused(self, running):
        base, _ = running
        with pytest.raises(urllib.error.HTTPError) as refused:
            post(base, None, raw=b"not json at all")
        assert refused.value.code == 400

    def test_nothing_else_accepts_a_post(self, running):
        base, _ = running
        request = urllib.request.Request(
            base + "/api/searches", data=b"{}", method="POST"
        )
        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(request)
        assert refused.value.code == 404
