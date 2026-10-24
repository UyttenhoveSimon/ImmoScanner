"""The command line: what it asks for, what it prints, what it writes."""

import json
from pathlib import Path
from typing import ClassVar

import pytest
from cyclopts import CycloptsError

import ImmoScanner.Console as console
from ImmoScanner.Archives.Store import Report
from ImmoScanner.ImmoScanner import ImmoScanner
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

    calls: ClassVar[list] = []

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

    @staticmethod
    def filter_by_condition(findings, condition="any"):
        return ImmoScanner.filter_by_condition(findings, condition)

    def get_insights(self, findings, renting=None):
        return {"listings": len(findings), "median_price": 350000.0}


@pytest.fixture(autouse=True)
def stub(monkeypatch):
    StubScanner.calls = []
    monkeypatch.setattr(console, "ImmoScanner", StubScanner)
    return StubScanner


def run(*tokens):
    """Run the command line as typed, without leaving the test on an error."""
    return console.app(
        list(tokens),
        exit_on_error=False,
        print_error=False,
        result_action="return_value",
    )


def call(name):
    return next(kwargs for called, kwargs in StubScanner.calls if called == name)


class TestRouting:
    def test_a_postal_code_starts_a_search(self, capsys):
        run("scan", "Belgium", "-p", "5000")
        assert call("research")["postal_code"] == "5000"
        assert "2 listings, 2 unique" in capsys.readouterr().out

    def test_a_city_starts_a_search(self):
        run("scan", "Belgium", "--city", "Namur")
        assert call("research")["city"] == "Namur"

    def test_a_url_goes_to_the_url_search(self):
        run("scan", "Belgium", "--url", "https://www.immoweb.be/fr/recherche/x")
        assert call("url")["url"] == "https://www.immoweb.be/fr/recherche/x"

    def test_the_search_terms_are_passed_on(self):
        run("scan", "Belgium", "-p", "5000", "--type", APARTMENT, "--rent")
        asked = call("research")
        assert asked["type"] == APARTMENT and asked["rent_or_buy"] == RENT

    def test_buying_is_the_default(self):
        run("scan", "Belgium", "-p", "5000")
        assert call("research")["rent_or_buy"] == BUY

    def test_a_search_without_a_place_is_refused(self):
        with pytest.raises(SystemExit):
            run("scan", "Belgium")

    def test_an_unknown_type_is_refused_before_scanning(self):
        with pytest.raises(CycloptsError):
            run("scan", "Belgium", "-p", "5000", "--type", "castle")
        assert StubScanner.calls == []

    def test_the_yield_run_short_circuits_the_rest(self, capsys):
        run("yield", "Belgium", "-p", "5000")
        assert [called for called, _ in StubScanner.calls] == ["yield"]
        assert "gross_yield_percent: 4.50" in capsys.readouterr().out


class TestExplorer:
    def test_serving_browses_an_archive_instead_of_scanning(self, monkeypatch):
        served = []
        monkeypatch.setattr(
            console.Server, "serve", lambda path, port: served.append((path, port))
        )

        run("serve", "a.db", "--port", "9001")

        assert served == [(Path("a.db"), 9001)]
        assert StubScanner.calls == []  # nothing was scanned

    def test_serving_needs_to_be_told_which_archive(self):
        with pytest.raises(CycloptsError):
            run("serve")


class TestSourceFilter:
    def test_the_lists_reach_the_scanner(self):
        run("scan", "Belgium", "-p", "5000", "--source", "homegate, immoscout24")
        assert call("filter")["keep"] == ["homegate", "immoscout24"]

    def test_exclusions_reach_the_scanner(self):
        run("scan", "Belgium", "-p", "5000", "--exclude-source", "Properstar")
        assert call("filter")["drop"] == ["Properstar"]

    def test_no_filter_is_still_a_filter_call_with_nothing_in_it(self):
        run("scan", "Belgium", "-p", "5000")
        assert call("filter") == {"keep": [], "drop": []}

    def test_what_the_filter_removed_is_reported(self, monkeypatch, capsys):
        monkeypatch.setattr(
            StubScanner,
            "filter_by_source",
            lambda self, results, keep=(), drop=(): [results[0][:1]],
        )
        run("scan", "Belgium", "-p", "5000", "--source", "homegate")

        assert (
            "2 listings, 1 from the asked sources, 1 unique" in capsys.readouterr().out
        )


class TestOutput:
    def test_the_findings_are_written_as_json(self, tmp_path):
        target = tmp_path / "out.json"
        run("scan", "Belgium", "-p", "5000", "-o", str(target))

        written = json.loads(target.read_text())
        assert [item["id"] for item in written] == ["1", "2"]
        assert "price_obj" not in written[0]  # not serialisable, never exported

    def test_the_file_is_announced(self, tmp_path, capsys):
        target = tmp_path / "out.json"
        run("scan", "Belgium", "-p", "5000", "-o", str(target))
        assert str(target) in capsys.readouterr().out


class TestArchive:
    def test_the_run_is_recorded_and_the_difference_printed(self, tmp_path, capsys):
        archive = tmp_path / "a.db"
        run("scan", "Belgium", "-p", "5000", "-s", str(archive))
        first = capsys.readouterr().out
        assert "2 new" in first

        run("scan", "Belgium", "-p", "5000", "-s", str(archive))
        assert "2 unchanged" in capsys.readouterr().out

    def test_the_archive_is_scoped_to_the_search(self, tmp_path, capsys):
        archive = tmp_path / "a.db"
        run("scan", "Belgium", "-p", "5000", "-s", str(archive))
        capsys.readouterr()

        run("scan", "Belgium", "-p", "1000", "-s", str(archive))
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
    def test_the_console_script_reads_argv(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv", ["immoscanner", "--debug", "scan", "Belgium", "-p", "5000"]
        )
        with pytest.raises(SystemExit) as finished:
            console.cli()
        assert finished.value.code == 0
        assert call("research")["postal_code"] == "5000"

    def test_every_question_is_a_subcommand(self, capsys):
        with pytest.raises(SystemExit):
            console.app(["--help"])
        printed = capsys.readouterr().out
        for command in ("scan", "brrrr", "yield", "serve"):
            assert command in printed


def needing(condition, listing_id, price, epc="", postal_code="4000"):
    item = listing(listing_id, price, epc=epc, postal_code=postal_code)
    item.condition = condition
    item.condition_reasons = [f"PEB {epc}"] if epc else []
    return item


class TestCondition:
    @pytest.fixture
    def market(self, stub, monkeypatch):
        findings = [
            needing("renovate", "a", 150000, epc="G"),
            needing("works", "b", 180000),
            needing("", "c", 250000),
        ]
        monkeypatch.setattr(
            StubScanner, "research_real_estate", lambda self, **kw: [findings]
        )
        return findings

    def test_only_listings_needing_work_are_shown(self, market, capsys, tmp_path):
        output = tmp_path / "out.json"
        run("scan", "Belgium", "-p", "4000", "-k", "works", "-o", str(output))

        printed = capsys.readouterr().out
        assert "2 of 3 need works" in printed
        assert "PEB G" in printed and "https://immoweb.be/a" in printed
        assert "https://immoweb.be/c" not in printed
        assert [row["id"] for row in json.loads(output.read_text())] == ["a", "b"]

    def test_the_market_statistics_cover_every_listing(self, market, capsys):
        run("scan", "Belgium", "-p", "4000", "-k", "renovate")
        assert "listings: 3" in capsys.readouterr().out

    def test_no_condition_lists_nothing_extra(self, market, capsys):
        run("scan", "Belgium", "-p", "4000")
        assert "need" not in capsys.readouterr().out


class TestBrrrr:
    @pytest.fixture
    def market(self, stub, monkeypatch):
        sale = [needing("", str(n), 200000) for n in range(5)] + [
            needing("renovate", "wreck", 100000, epc="F"),
            needing("works", "tired", 160000),
        ]
        rentals = [listing(f"r{n}", 900) for n in range(5)]

        def research(self, **kwargs):
            self._record("research", **kwargs)
            return [rentals if kwargs["rent_or_buy"] == RENT else sale]

        monkeypatch.setattr(StubScanner, "research_real_estate", research)

    def test_both_sides_of_the_market_are_scanned(self, market):
        run("brrrr", "Belgium", "-p", "4000")
        deals = [
            kw["rent_or_buy"] for name, kw in StubScanner.calls if name == "research"
        ]
        assert deals == [BUY, RENT]

    def test_fixer_uppers_are_ranked_by_discount(self, market, capsys, tmp_path):
        output = tmp_path / "brrrr.json"
        run(
            "brrrr", "Belgium", "-p", "4000", "--works-per-m2", "300", "-o", str(output)
        )

        printed = capsys.readouterr().out
        assert "to let: 5 listings, 5 unique" in printed
        assert "by postal code" in printed and "4000" in printed
        assert "2 listings needing works" in printed
        assert printed.index("immoweb.be/wreck") < printed.index("immoweb.be/tired")
        assert "-50% vs 2,000/m²" not in printed  # a discount reads as positive
        assert "+50% vs 2,000/m²" in printed
        assert "rent ~900/month" in printed

        rows = json.loads(output.read_text())
        assert [row["id"] for row in rows] == ["wreck", "tired"]
        assert rows[0]["equity"] == pytest.approx(200000 - 100000 - 30000)

    def test_renovate_narrows_the_candidates(self, market, capsys):
        run("brrrr", "Belgium", "-p", "4000", "-k", "renovate")
        printed = capsys.readouterr().out
        assert "1 listings needing renovate" in printed
        assert "immoweb.be/tired" not in printed

    def test_a_url_is_not_an_option(self):
        with pytest.raises(CycloptsError):
            run("brrrr", "Belgium", "--url", "https://www.immoweb.be/x")

    def test_a_place_is_needed(self):
        with pytest.raises(SystemExit):
            run("brrrr", "Belgium")

    def test_any_condition_still_means_some_work(self, market, capsys):
        run("brrrr", "Belgium", "-p", "4000", "-k", "any")
        assert "2 listings needing works" in capsys.readouterr().out

    def test_the_sale_scan_can_be_archived(self, market, tmp_path, capsys):
        run("brrrr", "Belgium", "-p", "4000", "-s", str(tmp_path / "a.db"))
        assert "7 new" in capsys.readouterr().out

    def test_thin_references_are_called_out(self, stub, monkeypatch, capsys):
        sale = [needing("renovate", "lone", 100000, postal_code="4020")]
        monkeypatch.setattr(
            StubScanner, "research_real_estate", lambda self, **kw: [sale]
        )
        run("brrrr", "Belgium", "-p", "4020")
        assert "(reference: scan; rent: scan)" in capsys.readouterr().out


class TestYieldOptions:
    def test_the_page_limit_and_region_reach_the_yield_scan(self):
        run("yield", "Belgium", "--region", "Liège", "-m", "4")
        asked = call("yield")
        assert (asked["region"], asked["max_pages"]) == ("Liège", 4)

    def test_a_place_is_needed(self):
        with pytest.raises(SystemExit):
            run("yield", "Belgium")


class TestDescribe:
    def test_a_listing_without_certificate_or_reasons(self):
        line = console.describe(listing("x", 250000, postal_code="4000", city="Liège"))
        assert "PEB" not in line and "[" not in line
        assert "250,000 EUR" in line and "2,500/m²" in line and "4000 Liège" in line

    def test_listings_are_printed_cheapest_per_m2_first(self, capsys):
        dear = listing("dear", 300000)
        cheap = listing("cheap", 120000)
        no_surface = listing("none", 90000, livable_square_meters=0)

        console.print_listings([dear, no_surface, cheap], top=5)

        printed = capsys.readouterr().out
        assert printed.index("/cheap") < printed.index("/dear")
        assert "/none" not in printed

    def test_top_limits_what_is_printed(self, capsys):
        console.print_listings([listing(str(n), 100000 + n) for n in range(5)], top=2)
        assert capsys.readouterr().out.count("https://") == 2
