"""The paths taken when a portal serves something less than its usual page.

The captured fixtures cover the happy path; these cover what each extractor
falls back on when a field is missing, and the defaults of the shared base.
"""

import pytest
from bs4 import BeautifulSoup

from ImmoScanner.Archives.Store import Store
from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Means.RealEstateResearch import ANY, BUY, RENT, RealEstateResearch
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult
from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb
from ImmoScanner.Workers.RealEstateWorker import RealEstateWorker


def fragment(markup):
    return BeautifulSoup(markup, "lxml")


class TestDefaults:
    """What a portal class inherits when it overrides nothing."""

    def test_a_portal_that_announces_no_total_walks_until_it_runs_out(self):
        assert RealEstateWorker().total_results(fragment("<html></html>")) is None

    def test_the_default_page_reader_selects_the_cards(self, monkeypatch):
        class Bare(RealEstateWorker):
            CARD_SELECTOR = "article"

            def url_builder(self, research, page=1):
                return f"https://x.test/{page}"

        worker = Bare()
        monkeypatch.setattr(
            worker,
            "get_html",
            lambda url, wait_for=(): "<article>a</article><article>b</article>",
        )
        items, total = worker.fetch_page(RealEstateResearch(), 1)
        assert len(items) == 2 and total is None

    def test_a_portal_with_nothing_to_probe_never_trusts_a_plain_get(self):
        assert RealEstateWorker().looks_complete("<html>anything</html>") is False


class TestHelpers:
    def test_the_text_of_nothing_is_empty(self):
        assert RealEstateWorker.visible_text(None) == ""

    def test_screen_reader_duplicates_are_dropped(self):
        node = fragment('<p>4 ch.<span class="sr-only">4 chambres</span></p>').p
        assert RealEstateWorker.visible_text(node) == "4 ch."

    def test_an_absent_currency_falls_back(self):
        assert RealEstateWorker.currency_code("", default="CHF") == "CHF"
        assert RealEstateWorker.currency_code(None) == ""

    @pytest.mark.parametrize(
        "symbol, code", [("€", "EUR"), ("chf", "CHF"), ("Fr.", "CHF"), ("$", "USD")]
    )
    def test_symbols_become_iso_codes(self, symbol, code):
        assert RealEstateWorker.currency_code(symbol) == code

    def test_an_unknown_currency_is_passed_through_untouched(self):
        assert RealEstateWorker.currency_code("SEK") == "SEK"


class TestPortalDefaults:
    @pytest.mark.parametrize(
        "worker_class, country",
        [(Immoweb, "Belgique"), (ImmoVlan, "Belgique"), (Comparis, "Switzerland")],
    )
    def test_a_search_without_a_country_gets_the_portal_s_own(
        self, worker_class, country
    ):
        research = RealEstateResearch(postal_code="1")
        worker_class().fill_empty_fields(research)
        assert research.country == country

    @pytest.mark.parametrize("worker_class", [Immoweb, ImmoVlan, Comparis])
    def test_a_country_already_set_is_left_alone(self, worker_class):
        research = RealEstateResearch(postal_code="1", country="Elsewhere")
        worker_class().fill_empty_fields(research)
        assert research.country == "Elsewhere"


class TestImmowebFallbacks:
    def test_a_card_without_a_link_is_not_given_the_home_page(self):
        card = fragment('<article class="card--result"></article>').article
        assert Immoweb().get_result_link(card) == ""

    def test_the_price_is_read_off_the_markup_when_there_is_no_screen_reader_copy(self):
        card = fragment(
            '<article class="card--result">'
            '<p class="card--result__price"><span>199 000 €</span></p>'
            "</article>"
        ).article
        assert Immoweb().get_result_price(card).amount == 199000


class TestImmoVlanFallbacks:
    def test_the_reference_is_taken_from_the_favourite_button_without_a_link(self):
        card = fragment(
            '<article class="v3-search-card">'
            '<button class="v3-search-card-favorite" data-value-id="VBE1">x</button>'
            "</article>"
        ).article
        assert ImmoVlan().get_result_id(card) == "VBE1"

    def test_the_link_is_taken_from_the_title_without_a_data_url(self):
        card = fragment(
            '<article class="v3-search-card">'
            '<h2 class="v3-search-card-title"><a href="/fr/detail/x">t</a></h2>'
            "</article>"
        ).article
        assert ImmoVlan().get_result_link(card) == "https://immovlan.be/fr/detail/x"

    def test_a_card_with_neither_has_no_reference(self):
        card = fragment('<article class="v3-search-card"></article>').article
        assert ImmoVlan().get_result_id(card) == ""

    def test_a_missing_measurement_reads_as_zero_not_as_an_error(self):
        card = fragment('<article class="v3-search-card"></article>').article
        assert ImmoVlan().get_livable_square_meters(card) == 0
        assert ImmoVlan().get_bedrooms_number(card) == 0

    def test_bedrooms_fall_back_to_the_pill_without_microdata(self):
        card = fragment(
            '<article class="v3-search-card">'
            '<span class="v3-search-card-pill"><strong>3</strong> Chambre(s)</span>'
            "</article>"
        ).article
        assert ImmoVlan().get_bedrooms_number(card) == 3

    def test_a_page_without_a_counter_announces_no_total(self):
        assert ImmoVlan().total_results(fragment("<html></html>")) is None

    def test_the_consent_banner_is_dismissed_while_reading_a_page(self, monkeypatch):
        worker = ImmoVlan()
        dismissed = []
        monkeypatch.setattr(
            worker, "get_html", lambda url, wait_for=(): "<html></html>"
        )
        monkeypatch.setattr(
            worker, "dismiss_banner", lambda selector: dismissed.append(selector)
        )

        worker.fetch_page(RealEstateResearch(postal_code="5000"), 1)
        assert dismissed == ["#didomi-notice-agree-button"]


class TestComparisFallbacks:
    def test_a_page_that_is_not_the_result_route_is_an_error(self):
        with pytest.raises(ValueError, match="__NEXT_DATA__"):
            Comparis().parse_result_data(fragment("<html></html>"), "https://x.test")

    def test_a_page_past_the_last_one_yields_nothing_to_walk(self, monkeypatch):
        worker = Comparis()
        monkeypatch.setattr(
            worker,
            "get_html",
            lambda url, wait_for=(): '<script id="__NEXT_DATA__">{"props":{"pageProps":{}}}</script>',
        )
        assert worker.fetch_page(RealEstateResearch(postal_code="1618"), 9) == (
            [],
            None,
        )

    def test_the_result_payload_is_read_through_the_fetch_ladder(self, monkeypatch):
        worker = Comparis()
        payload = (
            '<script id="__NEXT_DATA__">{"props":{"pageProps":{"initialResultData":'
            '{"numberOfResults":2,"resultItems":[]}}}}</script>'
        )
        monkeypatch.setattr(worker, "get_html", lambda url, wait_for=(): payload)
        assert worker.get_result_data("https://x.test")["numberOfResults"] == 2

    def test_an_address_that_does_not_start_with_a_postal_code(self):
        postal, city = Comparis().get_locality({"Address": ["Quelque part"]})
        assert (postal, city) == ("", "Quelque part")

    def test_an_item_with_no_address_at_all(self):
        assert Comparis().get_locality({}) == ("", "")

    def test_a_listing_sold_without_a_room_count(self):
        assert Comparis().get_rooms_number({"EssentialInformation": ["120 m²"]}) == 0


class TestResultModel:
    def test_a_price_per_square_metre_needs_both_halves(self):
        item = RealEstateResearchResult()
        item.price, item.livable_square_meters = 0, 100
        assert item.price_per_square_meter is None

        item.price, item.livable_square_meters = 300000, 0
        assert item.price_per_square_meter is None

        item.price, item.livable_square_meters = 300000, 100
        assert item.price_per_square_meter == 3000

    def test_a_result_describes_itself(self):
        item = RealEstateResearchResult()
        item.platform, item.id, item.city = "immoweb.be", "1", "Namur"
        assert "immoweb.be" in repr(item) and "Namur" in repr(item)


class TestArchiveEdges:
    def test_a_listing_the_portal_gave_no_id_is_not_archived(self, tmp_path):
        nameless = RealEstateResearchResult()
        nameless.platform, nameless.id, nameless.price = "immoweb.be", "", 1
        with Store(tmp_path / "a.db") as store:
            report = store.record("scope", [nameless])
        assert report.new == []


class TestGrossYield:
    def test_the_area_is_scanned_for_sale_and_to_let(self, monkeypatch):
        scanner = ImmoScanner()
        asked = []

        def fake_search(
            country_name, postal_code="", city="", type=ANY, rent_or_buy=BUY
        ):
            asked.append(rent_or_buy)
            price = 300000 if rent_or_buy == BUY else 1000
            item = RealEstateResearchResult()
            item.id, item.platform = rent_or_buy, "x"
            item.price, item.livable_square_meters = price, 100
            return [[item]]

        monkeypatch.setattr(scanner, "research_real_estate", fake_search)
        insights = scanner.research_gross_yield("Belgium", postal_code="5000")

        assert asked == [BUY, RENT]
        assert insights["median_price"] == 300000
        assert insights["rental_median_price"] == 1000
        assert insights["gross_yield_percent"] == pytest.approx(4.0)

    def test_an_unknown_country_is_refused_in_url_mode(self, monkeypatch):
        import ImmoScanner.ImmoScanner as module

        monkeypatch.setattr(
            module,
            "CountryFactory",
            lambda: type(
                "F", (), {"generate_country_given_name": lambda self, name: None}
            )(),
        )
        with pytest.raises(ValueError):
            ImmoScanner().research_real_estate_url("Atlantis", "https://x.test")
