import logging
import os
import time

import requests
from rustwright.sync_api import sync_playwright

try:
    # Optional: speaks a real browser's TLS and HTTP/2 handshake, which some
    # portals require even though they serve the page to anyone who does.
    from curl_cffi import requests as curl_requests
except ImportError:  # pragma: no cover - the ladder simply loses a rung
    curl_requests = None

logger = logging.getLogger(__name__)

# A plain desktop Chrome signature. Rustwright drives Chromium over raw CDP and
# never loads the Playwright Node driver, so the driver fingerprint is absent,
# but the default user agent still advertises a headless build.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_TIMEOUT_MS = 45_000
HTTP_TIMEOUT = 25

#: http clients to try, cheapest first, before falling back to the browser
HTTP_CLIENTS = ("requests", "curl_cffi")
#: the generic profile tracks the current Chrome; a pinned one ages out and
#: starts being refused (chrome131 already is, where "chrome" still passes)
CURL_IMPERSONATE = "chrome"


class Worker:
    """Fetches pages for one portal, over plain HTTP when that is enough.

    Fetching climbs a ladder, cheapest rung first: a plain GET, then the same
    GET behind a browser's TLS handshake, then a real browser. Most portals
    server-render their result lists and never leave the first rung. A rung is
    abandoned for good the first time it comes back short, so a portal that
    needs the top of the ladder pays for one wasted attempt per rung, not one
    per page.
    """

    def __init__(
        self,
        headless=True,
        locale="fr-BE",
        timezone_id="Europe/Brussels",
        http_clients=HTTP_CLIENTS,
    ):
        self.domain_name = ""
        self.headless = headless
        self.locale = locale
        self.timezone_id = timezone_id
        self.http_clients = [
            name
            for name in http_clients
            if name != "curl_cffi" or curl_requests is not None
        ]
        self.session = None
        #: set once a client has read a real result page from this portal
        self.http_proven = False
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def http_headers(self):
        return {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": f"{self.locale},fr;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
        }

    def start(self):
        """Start the browser session. Called lazily by the browser fetch path."""
        if self.page is not None:
            return self

        logger.debug(f"{self.domain_name}: starting the browser engine")
        self.playwright = sync_playwright().start()

        launch_options = {"headless": self.headless}
        executable_path = os.environ.get("IMMOSCANNER_BROWSER_PATH")
        if executable_path:
            launch_options["executable_path"] = executable_path

        self.browser = self.playwright.chromium.launch(**launch_options)
        self.context = self.browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            locale=self.locale,
            timezone_id=self.timezone_id,
            viewport=DEFAULT_VIEWPORT,
        )
        self.context.set_extra_http_headers(
            {
                "Accept-Language": f"{self.locale},fr;q=0.9,en;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self.context.set_default_timeout(DEFAULT_TIMEOUT_MS)
        self.page = self.context.new_page()
        return self

    def close(self):
        # A crashed browser must not mask the error that made us close.
        for release, resource in (
            ("close", self.session),
            ("close", self.context),
            ("close", self.browser),
            ("stop", self.playwright),
        ):
            if resource is None:
                continue
            try:
                getattr(resource, release)()
            except Exception as error:
                logger.debug(f"failed to release {resource!r}: {error}")

        self.session = None
        self.playwright = self.browser = self.context = self.page = None

    @property
    def http_client(self):
        """Name of the rung currently in use, or ``None`` once all are spent."""
        return self.http_clients[0] if self.http_clients else None

    def open_session(self):
        if self.session is not None:
            return self.session
        if self.http_client is None:
            return None

        if self.http_client == "curl_cffi":
            self.session = curl_requests.Session(impersonate=CURL_IMPERSONATE)
        else:
            self.session = requests.Session()
        self.session.headers.update(self.http_headers())
        return self.session

    def drop_http_client(self):
        """Give up on the current rung and move to the next one."""
        if self.session is not None:
            try:
                self.session.close()
            except Exception as error:
                logger.debug(f"failed to close the http session: {error}")
            self.session = None
        if self.http_clients:
            self.http_clients.pop(0)

    def fetch_over_http(self, url):
        """Return the page body, or ``None`` when this rung cannot read it."""
        session = self.open_session()
        if session is None:
            return None

        try:
            response = session.get(url, timeout=HTTP_TIMEOUT)
        except Exception as error:  # every client raises its own transport errors
            logger.debug(f"{self.domain_name}: {self.http_client} failed ({error})")
            return None

        if response.status_code != 200:
            logger.debug(
                f"{self.domain_name}: {self.http_client} got {response.status_code}"
            )
            return None

        return response.text

    def fetch_in_browser(self, url, wait_for=(), render_timeout=10_000):
        self.start()
        self.page.goto(url, wait_until="domcontentloaded")
        for selector in wait_for:
            try:
                # "attached", not the default "visible": what is awaited may be
                # a <script> holding the payload, which is never visible, and
                # waiting for visibility burns the whole timeout on every page.
                self.page.wait_for_selector(
                    selector, state="attached", timeout=render_timeout
                )
            except Exception:
                logger.debug(
                    f"{self.domain_name}: {selector!r} never rendered on {url}"
                )
        return self.page.content()

    def dismiss_banner(self, selector, timeout=3_000):
        """Click a consent banner if it shows up; never fail the scrape over it."""
        if self.page is None:
            return False
        try:
            self.page.click(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def wait(self, milliseconds):
        if self.page is not None:
            self.page.wait_for_timeout(milliseconds)
        else:
            time.sleep(milliseconds / 1000)
