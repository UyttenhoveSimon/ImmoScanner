import logging
import re
import urllib.parse

from bs4 import BeautifulSoup

from .Worker import Worker

logger = logging.getLogger(__name__)

# lxml recovers from the unclosed tags several portals ship; html.parser does not.
HTML_PARSER = "lxml"

# price_parser hands back whatever the page printed; portals are compared on
# their prices, so the code is normalised to ISO 4217 here.
CURRENCY_CODES = {
    "€": "EUR",
    "EUR": "EUR",
    "CHF": "CHF",
    "FR.": "CHF",
    "£": "GBP",
    "$": "USD",
}

BOT_WALL_MARKERS = (
    "captcha-delivery.com",
    "geo.captcha",
    "/cdn-cgi/challenge-platform",
)


class BotWallError(RuntimeError):
    """The portal served an anti-bot interstitial instead of the result list."""


class RealEstateWorker(Worker):
    #: hard stop so a broad search cannot walk hundreds of pages
    MAX_PAGES = 20
    #: courtesy pause between two result pages
    PAGE_DELAY_MS = 800
    #: how long to wait for a client-rendered block before giving up on it
    RENDER_TIMEOUT_MS = 10_000
    #: element that proves a plain GET returned the real result list
    PROBE_SELECTOR = None
    #: blocks to wait for when the browser path is used
    WAIT_FOR = ()
    #: the result cards on a search page
    CARD_SELECTOR = None

    def get_findings(self, real_estate_research):
        """Walk the result pages and turn every card into a result object.

        Page counts are not read off the page: immoweb renders its pagination
        and its total client-side, so a plain GET never sees them. Instead the
        walk stops on the first empty page, or as soon as the portal's own
        announced total has been collected.
        """
        self.fill_empty_fields(real_estate_research)
        results = []

        try:
            for page in range(1, self.MAX_PAGES + 1):
                if page > 1:
                    self.wait(self.PAGE_DELAY_MS)

                try:
                    items, total = self.fetch_page(real_estate_research, page)
                except Exception as error:
                    # A portal that has run out of pages may answer with
                    # something that is not a result list at all. Losing the
                    # pages already walked over that would be absurd, so the
                    # walk just stops - unless it never started.
                    if page == 1:
                        raise
                    logger.warning(
                        f"{self.domain_name}: stopping at page {page} ({error})"
                    )
                    break

                logger.debug(f"{self.domain_name}: page {page} -> {len(items)} cards")
                if not items:
                    break

                for item in items:
                    try:
                        results.append(self.extract_findings(item))
                    except Exception as error:
                        logger.warning(f"{self.domain_name}: skipped a card ({error})")

                # immoweb repeats a sponsored card on every page, so the stop
                # condition counts distinct listings, not rows.
                if total is not None and len({item.id for item in results}) >= total:
                    break
            else:
                logger.warning(
                    f"{self.domain_name}: stopped at the {self.MAX_PAGES} page cap"
                )
        finally:
            self.close()

        logger.info(f"{self.domain_name}: {len(results)} listings")
        return results

    def fetch_page(self, real_estate_research, page):
        """Return ``(raw items, announced total or None)`` for one result page."""
        soup = self.get_soup(
            self.url_builder(real_estate_research, page), wait_for=self.WAIT_FOR
        )
        return soup.select(self.CARD_SELECTOR), self.total_results(soup)

    def total_results(self, soup):
        """How many listings the portal says the search matched, if it says so."""
        return None

    def get_html(self, url, wait_for=()):
        """Fetch ``url``, over HTTP when the portal serves the list that way.

        A portal that answers an incomplete page once will answer incomplete
        pages for the rest of the run, so the worker stops trying HTTP after
        the first miss rather than paying for a wasted GET on every page.
        """
        if self.http_first:
            html = self.fetch_over_http(url)
            if html is not None and self.looks_complete(html):
                return html

            self.http_first = False
            logger.info(
                f"{self.domain_name}: plain http came back incomplete, "
                "switching to the browser engine"
            )

        return self.fetch_in_browser(url, wait_for, self.RENDER_TIMEOUT_MS)

    def looks_complete(self, html):
        if not self.PROBE_SELECTOR:
            return False
        return bool(BeautifulSoup(html, HTML_PARSER).select_one(self.PROBE_SELECTOR))

    def get_soup(self, url, wait_for=()):
        html = self.get_html(url, wait_for)
        self.raise_on_bot_wall(html)
        return BeautifulSoup(html, HTML_PARSER)

    def raise_on_bot_wall(self, html):
        for marker in BOT_WALL_MARKERS:
            if marker in html:
                raise BotWallError(
                    f"{self.domain_name} served an anti-bot challenge ({marker}); "
                    "no listing can be read from this page"
                )

    @staticmethod
    def visible_text(node):
        """Text of a node with the screen-reader-only duplicates stripped out."""
        if node is None:
            return ""
        clone = BeautifulSoup(str(node), HTML_PARSER)
        for hidden in clone.select(".sr-only"):
            hidden.decompose()
        return re.sub(r"\s+", " ", clone.get_text(" ", strip=True)).strip()

    @staticmethod
    def with_query_param(url, name, value):
        """Return ``url`` with ``name=value`` set, replacing any existing value.

        Used to paginate a search url supplied by the caller, which otherwise
        would be fetched unchanged for every page.
        """
        parts = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        query[name] = str(value)
        return urllib.parse.urlunsplit(
            parts._replace(query=urllib.parse.urlencode(query))
        )

    @staticmethod
    def currency_code(currency, default=""):
        if not currency:
            return default
        return CURRENCY_CODES.get(currency.strip().upper(), currency.strip())

    @staticmethod
    def first_int(text, default=0):
        match = re.search(r"\d[\d\s.,]*", text or "")
        if not match:
            return default
        digits = re.sub(r"[^\d]", "", match.group())
        return int(digits) if digits else default
