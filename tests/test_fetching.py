"""The fetch ladder and the page walk, without touching the network."""

import pytest

from ImmoScanner.Means.RealEstateResearch import RealEstateResearch
from ImmoScanner.Workers.RealEstateWorker import BotWallError, RealEstateWorker

PAGE = "<html><body><article class='card'>a</article></body></html>"
EMPTY = "<html><body></body></html>"


class FakeWorker(RealEstateWorker):
    """A worker whose pages come from a script instead of a portal."""

    CARD_SELECTOR = "article.card"
    PROBE_SELECTOR = CARD_SELECTOR

    def __init__(self, http_answers=None, browser_answer=PAGE, **kwargs):
        super().__init__(**kwargs)
        self.domain_name = "fake.test"
        self.http_answers = list(http_answers or [])
        self.browser_answer = browser_answer
        self.http_calls = []
        self.browser_calls = 0

    def fetch_over_http(self, url):
        self.http_calls.append(self.http_client)
        return self.http_answers.pop(0) if self.http_answers else None

    def fetch_in_browser(self, url, wait_for=(), render_timeout=0):
        self.browser_calls += 1
        return self.browser_answer

    def close(self):
        pass

    def fill_empty_fields(self, research):
        pass

    def url_builder(self, research, page=1):
        return f"https://fake.test/?page={page}"

    def extract_findings(self, card):
        raise NotImplementedError


class TestLadder:
    def test_stays_on_the_cheapest_client_that_works(self):
        worker = FakeWorker(http_answers=[PAGE, PAGE])
        worker.get_html("u")
        worker.get_html("u")
        assert worker.http_calls == ["requests", "requests"]
        assert worker.browser_calls == 0

    def test_climbs_when_the_first_client_comes_back_short(self):
        worker = FakeWorker(http_answers=[EMPTY, PAGE])
        assert worker.get_html("u") == PAGE
        assert worker.http_calls == ["requests", "curl_cffi"]
        assert worker.browser_calls == 0

    def test_falls_to_the_browser_once_every_client_is_spent(self):
        worker = FakeWorker(http_answers=[EMPTY, EMPTY])
        assert worker.get_html("u") == PAGE
        assert worker.http_client is None
        assert worker.browser_calls == 1

    def test_a_spent_ladder_is_not_retried_on_the_next_page(self):
        worker = FakeWorker(http_answers=[EMPTY, EMPTY])
        worker.get_html("u")
        worker.get_html("u")
        assert worker.http_calls == ["requests", "curl_cffi"]
        assert worker.browser_calls == 2

    def test_a_miss_after_a_success_ends_the_results_rather_than_the_client(self):
        """A portal answers 404 for a page past the last one.

        That is the walk finishing, not the client going blind, so the rung
        must survive it - demoting here would restart the scan in a browser.
        """
        worker = FakeWorker(http_answers=[PAGE, None])
        worker.get_html("u")
        assert worker.get_html("u") == ""
        assert worker.http_client == "requests"
        assert worker.browser_calls == 0

    def test_curl_cffi_is_dropped_from_the_ladder_when_not_installed(self):
        worker = FakeWorker(http_clients=("requests",))
        assert worker.http_clients == ["requests"]


class TestPageWalk:
    def walker(self, pages, totals=None):
        worker = FakeWorker()
        worker.PAGE_DELAY_MS = 0
        calls = []

        def fetch_page(research, page):
            calls.append(page)
            index = page - 1
            items = pages[index] if index < len(pages) else []
            total = (totals or [None] * len(pages))[index] if totals else None
            return items, total

        worker.fetch_page = fetch_page
        worker.extract_findings = lambda item: item
        worker.pages_requested = calls
        return worker

    def test_stops_on_the_first_empty_page(self):
        worker = self.walker([["a", "b"], ["c"], []])
        assert worker.get_findings(RealEstateResearch()) == ["a", "b", "c"]
        assert worker.pages_requested == [1, 2, 3]

    def test_stops_as_soon_as_the_announced_total_is_reached(self):
        class Item:
            def __init__(self, id):
                self.id = id

        worker = self.walker([[Item("1"), Item("2")], [Item("3")]], totals=[3, 3])
        assert len(worker.get_findings(RealEstateResearch())) == 3
        assert worker.pages_requested == [1, 2]  # no wasted third request

    def test_counts_distinct_listings_against_the_total(self):
        """immoweb repeats one sponsored card on every page."""

        class Item:
            def __init__(self, id):
                self.id = id

        worker = self.walker(
            [[Item("ad"), Item("1")], [Item("ad"), Item("2")], []], totals=[3, 3, 3]
        )
        results = worker.get_findings(RealEstateResearch())

        # four rows fetched, three distinct listings: the walk stops on the
        # third distinct one rather than on the third row
        assert len(results) == 4
        assert len({item.id for item in results}) == 3
        assert worker.pages_requested == [1, 2]

    def test_honours_the_page_cap(self):
        worker = self.walker([["a"]] * 50)
        worker.MAX_PAGES = 3
        assert len(worker.get_findings(RealEstateResearch())) == 3
        assert worker.pages_requested == [1, 2, 3]

    def test_keeps_the_pages_it_already_walked_when_a_later_one_fails(self):
        worker = FakeWorker()
        worker.PAGE_DELAY_MS = 0
        worker.extract_findings = lambda item: item

        def fetch_page(research, page):
            if page == 1:
                return ["a", "b"], None
            raise ValueError("the portal stopped making sense")

        worker.fetch_page = fetch_page
        assert worker.get_findings(RealEstateResearch()) == ["a", "b"]

    def test_a_failure_on_the_very_first_page_is_raised(self):
        worker = FakeWorker()
        worker.fetch_page = lambda research, page: (_ for _ in ()).throw(
            ValueError("boom")
        )
        with pytest.raises(ValueError):
            worker.get_findings(RealEstateResearch())

    def test_a_single_unreadable_card_does_not_lose_the_page(self):
        worker = self.walker([["good", "bad", "good"], []])

        def extract(item):
            if item == "bad":
                raise ValueError("unparseable")
            return item

        worker.extract_findings = extract
        assert worker.get_findings(RealEstateResearch()) == ["good", "good"]


class TestBotWall:
    def test_a_captcha_interstitial_is_an_error_not_an_empty_market(self):
        worker = FakeWorker()
        with pytest.raises(BotWallError):
            worker.raise_on_bot_wall(
                '<iframe src="https://geo.captcha-delivery.com/captcha/"></iframe>'
            )

    def test_an_ordinary_page_passes(self):
        FakeWorker().raise_on_bot_wall(PAGE)
