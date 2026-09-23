import logging
import os
import time

import requests
from rustwright.sync_api import sync_playwright

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


class Worker:
    """Fetches pages for one portal, over plain HTTP when that is enough.

    Several portals server-render their result lists, which a single GET reads
    an order of magnitude faster than a browser can. A browser session is only
    started when HTTP comes back incomplete, and it then stays up for the rest
    of the worker's life; ``close()`` releases it.
    """

    def __init__(
        self,
        headless=True,
        locale="fr-BE",
        timezone_id="Europe/Brussels",
        http_first=True,
    ):
        self.domain_name = ""
        self.headless = headless
        self.locale = locale
        self.timezone_id = timezone_id
        self.http_first = http_first
        self.session = None
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

    def fetch_over_http(self, url):
        """Return the page body, or ``None`` when the portal refuses a plain GET."""
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(self.http_headers())

        try:
            response = self.session.get(url, timeout=HTTP_TIMEOUT)
        except requests.RequestException as error:
            logger.debug(f"{self.domain_name}: http fetch failed ({error})")
            return None

        if response.status_code != 200:
            logger.debug(f"{self.domain_name}: http fetch got {response.status_code}")
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
