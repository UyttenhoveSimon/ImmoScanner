"""The command line: what it asks for, what it prints, what it writes."""

import json

import pytest

import ImmoScanner.Console as console
from ImmoScanner.Archives.Store import Report
from ImmoScanner.Means.RealEstateResearch import APARTMENT, BUY, RENT
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult


def listing(listing_id="1", price=300000, **extra):
    item = RealEstateResearchResult()
    item.id = listing_id
    item.platform = "immoweb.be"
    item.price = price
    item.price_text = f"{price:,} €"
    item.currency = "EUR"
    item.city = "Namur"
    item.url = f"https://immoweb.be/{listing_id}"
    item.livable_square_meters = 100
    for name, value in extra.items():
        setattr(item, name, value)
    return item


class StubScanner:
    """Records what the cli asked of the scanner, and answers plausibly."""

    calls = None

    def __init__(self):
        StubScanner.calls = self.calls if self.calls is not None else []
        self.findings = [listing("1"), listing("2", 400000)]

    def _record(self, name, **kwargs):
        StubScanner.calls.append((name, kwargs))

    def research_real_estate(self, **kwargs):
        self._record("research", **kwargs)
        return [self.findings]

    def research_real_estate_url(self, **kwargs):
        self._record("url", **kwargs)
        return [self.findings]

    def research_gross_yield(self, **kwargs):
        self._record("yield", **kwargs)
        return {"gross_yield_percent": 4.5}

    def filter_by_source(self, results, keep=(), drop=()):
        self._record("filter", keep=list(keep), drop=list(drop))
        return results

    def duplicate_finder(self, results):
        return [item for group in results for item in group]

    def get_insights(self, findings, renting=None):
        return {"listings": len(findings), "median_price": 350000.0}


@pytest.fixture(autouse=True)
def stub(monkeypatch):
    StubScanner.calls = []
    monkeypatch.setattr(console, "ImmoScanner", StubScanner)
    return StubScanner


def call(name):
    return next(kwargs for called, kwargs in StubScanner.calls if called == name)


class TestRouting:
    def test_a_postal_code_starts_a_search(self, capsys):
        console.main("Belgium", postal_code="5000")
        assert call("research")["postal_code"] == "5000"
        assert "2 listings, 2 unique" in capsys.readouterr().out

    def test_a_city_starts_a_search(self):
        console.main("Belgium", city="Namur")
        assert call("research")["city"] == "Namur"

    def test_a_url_goes_to_the_url_search(self):
        console.main("Belgium", url="https://www.immoweb.be/fr/recherche/x")
        assert call("url")["url"] == "https://www.immoweb.be/fr/recherche/x"

    def test_the_search_terms_are_passed_on(self):
        console.main("Belgium", postal_code="5000", type=APARTMENT, rent=True)
        asked = call("research")
        assert asked["type"] == APARTMENT and asked["rent_or_buy"] == RENT

    def test_buying_is_the_default(self):
        console.main("Belgium", postal_code="5000")
        assert call("research")["rent_or_buy"] == BUY

    def test_a_search_without_a_place_is_refused(self):
        with pytest.raises(SystemExit):
            console.main("Belgium")

    def test_the_yield_run_short_circuits_the_rest(self, capsys):
        console.main("Belgium", postal_code="5000", yield_=True)
        assert [called for called, _ in StubScanner.calls] == ["yield"]
        assert "gross_yield_percent: 4.50" in capsys.readouterr().out


class TestSourceFilter:
    def test_the_lists_reach_the_scanner(self):
        console.main("Belgium", postal_code="5000", source="homegate, immoscout24")
        assert call("filter")["keep"] == ["homegate", "immoscout24"]

    def test_exclusions_reach_the_scanner(self):
        console.main("Belgium", postal_code="5000", exclude_source="Properstar")
        assert call("filter")["drop"] == ["Properstar"]

    def test_no_filter_is_still_a_filter_call_with_nothing_in_it(self):
        console.main("Belgium", postal_code="5000")
        assert call("filter") == {"keep": [], "drop": []}

    def test_what_the_filter_removed_is_reported(self, monkeypatch, capsys):
        monkeypatch.setattr(
            StubScanner,
            "filter_by_source",
            lambda self, results, keep=(), drop=(): [results[0][:1]],
        )
        console.main("Belgium", postal_code="5000", source="homegate")

        assert (
            "2 listings, 1 from the asked sources, 1 unique" in capsys.readouterr().out
        )


class TestOutput:
    def test_the_findings_are_written_as_json(self, tmp_path):
        target = tmp_path / "out.json"
        console.main("Belgium", postal_code="5000", output=str(target))

        written = json.loads(target.read_text())
        assert [item["id"] for item in written] == ["1", "2"]
        assert "price_obj" not in written[0]  # not serialisable, never exported

    def test_the_file_is_announced(self, tmp_path, capsys):
        target = tmp_path / "out.json"
        console.main("Belgium", postal_code="5000", output=str(target))
        assert str(target) in capsys.readouterr().out


class TestArchive:
    def test_the_run_is_recorded_and_the_difference_printed(self, tmp_path, capsys):
        archive = tmp_path / "a.db"
        console.main("Belgium", postal_code="5000", store=str(archive))
        first = capsys.readouterr().out
        assert "2 new" in first

        console.main("Belgium", postal_code="5000", store=str(archive))
        assert "2 unchanged" in capsys.readouterr().out

    def test_the_archive_is_scoped_to_the_search(self, tmp_path, capsys):
        archive = tmp_path / "a.db"
        console.main("Belgium", postal_code="5000", store=str(archive))
        capsys.readouterr()

        console.main("Belgium", postal_code="1000", store=str(archive))
        # a different search must not report the first one's listings as gone
        assert "0 gone" in capsys.readouterr().out


class TestPrinting:
    def test_a_ratio_keeps_its_decimals(self, capsys):
        console.print_insights({"gross_yield_percent": 4.4268})
        assert "4.43" in capsys.readouterr().out

    def test_a_price_is_rounded_and_grouped(self, capsys):
        console.print_insights({"median_price": 443521.27})
        assert "443,521" in capsys.readouterr().out

    def test_a_count_is_printed_as_it_is(self, capsys):
        console.print_insights({"listings": 111})
        assert "listings: 111" in capsys.readouterr().out

    def test_the_report_names_what_changed(self, capsys):
        report = Report(
            new=[listing("1")],
            price_changes=[(listing("2", 275000), 300000.0)],
            gone=[{"price": 289000.0, "city": "Namur", "url": "https://x/9"}],
            unchanged=7,
        )
        console.print_report(report)
        printed = capsys.readouterr().out

        assert "1 new, 1 repriced, 1 gone, 7 unchanged" in printed
        assert "down" in printed and "300,000 -> 275,000" in printed
        assert "gone" in printed and "https://x/9" in printed

    def test_a_rise_is_told_apart_from_a_cut(self, capsys):
        console.print_report(Report(price_changes=[(listing("2", 320000), 300000.0)]))
        assert "up" in capsys.readouterr().out

    def test_a_listing_seen_for_the_first_time_has_no_previous_price(self, capsys):
        console.print_report(Report(price_changes=[(listing("2"), None)]))
        assert "->" not in capsys.readouterr().out


class TestEntryPoint:
    def test_the_console_script_hands_argv_to_plac(self, monkeypatch):
        called = []
        monkeypatch.setattr(console.plac, "call", called.append)
        console.cli()
        assert called == [console.main]
