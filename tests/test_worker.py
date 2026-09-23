"""The fetching plumbing: http sessions, the browser session, and their release."""

import pytest

import ImmoScanner.Workers.Worker as worker_module
from ImmoScanner.Workers.Worker import Worker


class FakeResponse:
    def __init__(self, status_code=200, text="page"):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, response=None, error=None):
        self.headers = {}
        self.response = response or FakeResponse()
        self.error = error
        self.closed = False
        self.requests = []

    def get(self, url, timeout=None):
        self.requests.append((url, timeout))
        if self.error:
            raise self.error
        return self.response

    def close(self):
        self.closed = True


class FakePage:
    def __init__(self, content="<html></html>", missing=()):
        self._content = content
        self.missing = set(missing)
        self.goto_calls = []
        self.waited = []
        self.clicked = []
        self.timeouts = []

    def goto(self, url, wait_until=None):
        self.goto_calls.append((url, wait_until))

    def wait_for_selector(self, selector, state=None, timeout=None):
        self.waited.append((selector, state))
        if selector in self.missing:
            raise TimeoutError(f"{selector} never showed up")

    def click(self, selector, timeout=None):
        if selector in self.missing:
            raise TimeoutError("no such banner")
        self.clicked.append(selector)

    def wait_for_timeout(self, milliseconds):
        self.timeouts.append(milliseconds)

    def content(self):
        return self._content


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.headers = None
        self.timeout = None
        self.closed = False

    def set_extra_http_headers(self, headers):
        self.headers = headers

    def set_default_timeout(self, timeout):
        self.timeout = timeout

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, context):
        self.context = context
        self.context_options = None
        self.closed = False

    def new_context(self, **options):
        self.context_options = options
        return self.context

    def close(self):
        self.closed = True


class FakeEngine:
    def __init__(self, page):
        self.chromium = self
        self.browser = FakeBrowser(FakeContext(page))
        self.launch_options = None
        self.stopped = False

    def start(self):
        return self

    def launch(self, **options):
        self.launch_options = options
        return self.browser

    def stop(self):
        self.stopped = True


@pytest.fixture
def engine(monkeypatch):
    def install(page=None):
        built = FakeEngine(page or FakePage())
        monkeypatch.setattr(worker_module, "sync_playwright", lambda: built)
        return built

    return install


class TestHttpSession:
    def test_the_first_rung_is_a_plain_session(self, monkeypatch):
        made = FakeSession()
        monkeypatch.setattr(worker_module.requests, "Session", lambda: made)
        worker = Worker()

        assert worker.open_session() is made
        assert worker.http_client == "requests"
        assert "User-Agent" in made.headers

    def test_the_second_rung_impersonates_a_browser(self, monkeypatch):
        made = FakeSession()
        recorded = {}

        class FakeCurl:
            @staticmethod
            def Session(impersonate=None):
                recorded["impersonate"] = impersonate
                return made

        monkeypatch.setattr(worker_module, "curl_requests", FakeCurl)
        worker = Worker()
        worker.drop_http_client()

        assert worker.open_session() is made
        assert recorded["impersonate"] == worker_module.CURL_IMPERSONATE

    def test_the_profile_is_never_a_pinned_version(self):
        """chrome131 is already refused where the generic profile passes."""
        assert worker_module.CURL_IMPERSONATE == "chrome"

    def test_the_session_is_reused_between_requests(self, monkeypatch):
        sessions = [FakeSession(), FakeSession()]
        monkeypatch.setattr(worker_module.requests, "Session", lambda: sessions.pop(0))
        worker = Worker()
        assert worker.open_session() is worker.open_session()

    def test_dropping_a_rung_closes_its_session(self, monkeypatch):
        made = FakeSession()
        monkeypatch.setattr(worker_module.requests, "Session", lambda: made)
        worker = Worker()
        worker.open_session()
        worker.drop_http_client()

        assert made.closed
        assert worker.http_client == "curl_cffi"

    def test_a_session_that_refuses_to_close_still_frees_the_rung(self, monkeypatch):
        class Stubborn(FakeSession):
            def close(self):
                raise RuntimeError("already gone")

        monkeypatch.setattr(worker_module.requests, "Session", lambda: Stubborn())
        worker = Worker()
        worker.open_session()

        worker.drop_http_client()

        assert worker.session is None
        assert worker.http_client == "curl_cffi"

    def test_an_exhausted_ladder_opens_nothing(self):
        worker = Worker(http_clients=())
        assert worker.http_client is None
        assert worker.open_session() is None

    def test_curl_cffi_leaves_the_ladder_when_it_is_not_installed(self, monkeypatch):
        monkeypatch.setattr(worker_module, "curl_requests", None)
        assert Worker().http_clients == ["requests"]

    def test_the_language_header_follows_the_locale(self):
        assert "fr-CH" in Worker(locale="fr-CH").http_headers()["Accept-Language"]


class TestFetchOverHttp:
    def worker_with(self, monkeypatch, session):
        monkeypatch.setattr(worker_module.requests, "Session", lambda: session)
        return Worker()

    def test_a_good_answer_comes_back_as_text(self, monkeypatch):
        worker = self.worker_with(monkeypatch, FakeSession(FakeResponse(200, "hello")))
        assert worker.fetch_over_http("https://x.test") == "hello"

    @pytest.mark.parametrize("status", [301, 403, 404, 429, 500])
    def test_anything_but_200_is_a_miss(self, monkeypatch, status):
        worker = self.worker_with(monkeypatch, FakeSession(FakeResponse(status, "no")))
        assert worker.fetch_over_http("https://x.test") is None

    def test_a_transport_failure_is_a_miss_not_a_crash(self, monkeypatch):
        """Each client raises its own error type; none of them must escape."""
        worker = self.worker_with(monkeypatch, FakeSession(error=OSError("no route")))
        assert worker.fetch_over_http("https://x.test") is None

    def test_an_exhausted_ladder_fetches_nothing(self):
        assert Worker(http_clients=()).fetch_over_http("https://x.test") is None


class TestBrowserSession:
    def test_the_engine_starts_only_when_it_is_needed(self, engine):
        started = engine()
        worker = Worker()
        assert worker.page is None

        worker.start()
        assert worker.page is not None
        assert started.launch_options == {"headless": True}

    def test_starting_twice_keeps_one_session(self, engine):
        engine()
        worker = Worker()
        assert worker.start().page is worker.start().page

    def test_the_context_carries_the_locale_and_a_desktop_viewport(self, engine):
        started = engine()
        Worker(locale="fr-CH", timezone_id="Europe/Zurich").start()

        options = started.browser.context_options
        assert options["locale"] == "fr-CH"
        assert options["timezone_id"] == "Europe/Zurich"
        assert options["viewport"] == worker_module.DEFAULT_VIEWPORT

    def test_a_chromium_can_be_pointed_at_by_environment(self, engine, monkeypatch):
        started = engine()
        monkeypatch.setenv("IMMOSCANNER_BROWSER_PATH", "/opt/chromium")
        Worker().start()
        assert started.launch_options["executable_path"] == "/opt/chromium"

    def test_the_page_is_awaited_by_attachment_not_by_visibility(self, engine):
        """A <script> holding the payload is never visible."""
        page = FakePage(content="<html>ok</html>")
        engine(page)
        worker = Worker()

        assert (
            worker.fetch_in_browser("https://x.test", ("script#data",))
            == "<html>ok</html>"
        )
        assert page.waited == [("script#data", "attached")]
        assert page.goto_calls == [("https://x.test", "domcontentloaded")]

    def test_a_block_that_never_renders_does_not_fail_the_fetch(self, engine):
        """A single-page result has no pagination to wait for."""
        page = FakePage(content="<html>ok</html>", missing=["nav.pagination"])
        engine(page)
        assert (
            Worker().fetch_in_browser("https://x.test", ("nav.pagination",))
            == "<html>ok</html>"
        )


class TestBanners:
    def test_a_banner_is_clicked_when_it_is_there(self, engine):
        page = FakePage()
        engine(page)
        worker = Worker()
        worker.start()

        assert worker.dismiss_banner("#agree") is True
        assert page.clicked == ["#agree"]

    def test_a_missing_banner_is_not_a_failure(self, engine):
        engine(FakePage(missing=["#agree"]))
        worker = Worker()
        worker.start()
        assert worker.dismiss_banner("#agree") is False

    def test_there_is_nothing_to_dismiss_without_a_browser(self):
        assert Worker().dismiss_banner("#agree") is False


class TestWaiting:
    def test_the_browser_clock_is_used_when_there_is_a_page(self, engine):
        page = FakePage()
        engine(page)
        worker = Worker()
        worker.start()
        worker.wait(250)
        assert page.timeouts == [250]

    def test_otherwise_the_process_simply_sleeps(self, monkeypatch):
        slept = []
        monkeypatch.setattr(worker_module.time, "sleep", slept.append)
        Worker().wait(250)
        assert slept == [0.25]


class TestRelease:
    def test_everything_is_released_and_forgotten(self, engine, monkeypatch):
        session = FakeSession()
        monkeypatch.setattr(worker_module.requests, "Session", lambda: session)
        started = engine()
        worker = Worker()
        worker.open_session()
        worker.start()

        worker.close()

        assert (
            session.closed and started.browser.closed and started.browser.context.closed
        )
        assert started.stopped
        assert (worker.session, worker.browser, worker.context, worker.page) == (
            None,
        ) * 4

    def test_a_resource_that_refuses_to_close_does_not_mask_the_rest(self, engine):
        started = engine()
        started.browser.context.close = lambda: (_ for _ in ()).throw(
            RuntimeError("gone")
        )
        worker = Worker()
        worker.start()

        worker.close()

        assert started.browser.closed and started.stopped

    def test_closing_an_unused_worker_is_harmless(self):
        Worker().close()

    def test_the_worker_releases_itself_on_the_way_out(self, engine):
        started = engine()
        with Worker() as worker:
            worker.start()
        assert started.stopped
