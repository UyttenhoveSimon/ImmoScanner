"""The command line: one subcommand per kind of question asked of the portals."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict

from cyclopts import App, Parameter

from .Archives.Store import Store
from .ImmoScanner import ImmoScanner
from .Intellectuals import Brrrr
from .Intellectuals.Renovation import WORKS
from .Means.RealEstateResearch import ANY, BUY, RENT
from .Showrooms import Server

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .Archives.Store import Report
    from .ImmoScanner import Listings
    from .Means.RealEstateResearchResult import RealEstateResearchResult

#: yields and per-m2 rents lose all meaning rounded to the unit
ROUNDING_THRESHOLD = 100

Row = dict[str, Any]
PropertyType = Literal["any", "house", "apartment"]
Condition = Literal["any", "works", "renovate"]

app = App(
    name="immoscanner",
    help="Scan real estate portals for a town, a province or a canton.",
)


class Where(TypedDict):
    """Where to search and for what: the part every scan of a run shares."""

    postal_code: str
    city: str
    region: str
    type: str
    max_pages: int


@Parameter(name="*")
@dataclass(frozen=True, kw_only=True)
class Area:
    """Where to look, and what for.

    Parameters
    ----------
    postal_code
        Postal code to search; several can be given comma separated.
    city
        Town to search; its postal code is looked up when not given.
    region
        Province or canton to search whole.
    type
        Kind of property.
    max_pages
        Result pages to read per portal; 0 keeps each portal's default.
    source
        Keep only listings first published on these portals, comma separated.
    exclude_source
        Drop listings first published on these portals, comma separated.
    """

    postal_code: Annotated[str, Parameter(alias="-p")] = ""
    city: Annotated[str, Parameter(alias="-c")] = ""
    region: Annotated[str, Parameter(alias="-g")] = ""
    type: Annotated[PropertyType, Parameter(alias="-t")] = "any"
    max_pages: Annotated[int, Parameter(alias="-m")] = 0
    source: str = ""
    exclude_source: str = ""

    @property
    def place(self) -> str:
        return self.region or self.postal_code or self.city

    def where(self) -> Where:
        return {
            "postal_code": self.postal_code,
            "city": self.city,
            "region": self.region,
            "type": self.type,
            "max_pages": self.max_pages,
        }


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    debug: bool = False,
) -> None:
    """Set up logging, then run the subcommand.

    Parameters
    ----------
    debug
        Log every listing as it is read.
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    app(tokens)


@app.command
def scan(
    country: str,
    area: Area | None = None,
    *,
    url: Annotated[str, Parameter(alias="-u")] = "",
    rent: Annotated[bool, Parameter(alias="-r")] = False,
    condition: Annotated[Condition, Parameter(alias="-k")] = "any",
    top: Annotated[int, Parameter(alias="-l")] = 15,
    output: Annotated[Path | None, Parameter(alias="-o")] = None,
    store: Annotated[Path | None, Parameter(alias="-s")] = None,
) -> None:
    """Scan a place, print its price statistics, and what changed since last time.

    Parameters
    ----------
    country
        Belgium or Switzerland.
    url
        A search page copied from a portal, scanned instead of a place.
    rent
        Look at rentals instead of properties for sale.
    condition
        Only show listings needing at least this much work.
    top
        How many listings to print.
    output
        Write the listings shown to this JSON file.
    store
        SQLite archive to record the scan in and compare it against.
    """
    area = area or Area()
    if not (url or area.place):
        sys.exit("provide one of --postal-code, --city, --region or --url")

    scanner = ImmoScanner()
    deal = RENT if rent else BUY
    findings = Search(scanner, country, area, url).scan(deal)
    print_insights(scanner.get_insights(findings))
    if store:
        record(store, country, area, deal, findings)

    rows = report_condition(scanner, findings, condition, top)
    if output:
        write_json(output, rows)


@app.command
def brrrr(
    country: str,
    area: Area | None = None,
    *,
    condition: Annotated[Condition, Parameter(alias="-k")] = "works",
    works_per_m2: Annotated[float, Parameter(alias="-e")] = 0.0,
    top: Annotated[int, Parameter(alias="-l")] = 15,
    output: Annotated[Path | None, Parameter(alias="-o")] = None,
    store: Annotated[Path | None, Parameter(alias="-s")] = None,
) -> None:
    """Rank fixer-uppers against the postal code they stand in.

    Scans for sale and to let, then measures every listing that needs work
    against the median price per m2 of the listings around it needing none.

    Parameters
    ----------
    country
        Belgium or Switzerland.
    condition
        The least work a candidate must need; "any" still means some.
    works_per_m2
        Renovation budget per m2, off the equity and onto the cost.
    top
        How many listings to print.
    output
        Write the ranked listings to this JSON file.
    store
        SQLite archive to record the sale scan in and compare it against.
    """
    area = area or Area()
    if not area.place:
        sys.exit("provide one of --postal-code, --city or --region")

    scanner = ImmoScanner()
    search = Search(scanner, country, area)
    findings = search.scan(BUY)
    print_insights(scanner.get_insights(findings))
    if store:
        record(store, country, area, BUY, findings)

    rows = report_brrrr(search, findings, condition, works_per_m2, top)
    if output:
        write_json(output, rows)


@app.command(name="yield")
def gross_yield(country: str, area: Area | None = None) -> None:
    """Scan for sale and to let, and report the gross rental yield.

    Parameters
    ----------
    country
        Belgium or Switzerland.
    """
    area = area or Area()
    if not area.place:
        sys.exit("provide one of --postal-code, --city or --region")
    scanner = ImmoScanner()
    print_insights(scanner.research_gross_yield(country_name=country, **area.where()))


@app.command
def serve(
    store: Path, *, port: Annotated[int, Parameter(alias="-n")] = Server.DEFAULT_PORT
) -> None:
    """Browse a scan archive in the web explorer.

    Parameters
    ----------
    store
        SQLite archive written by scan --store.
    port
        Port the explorer listens on.
    """
    Server.serve(store, port=port)


def record(
    store: Path, country: str, area: Area, deal: str, findings: Listings
) -> None:
    # the archive follows the whole market, whatever is shown afterwards
    with Store(store) as archive:
        key = archive.search_key(country, area.place, area.type, deal)
        print_report(archive.record(key, findings))


class Search:
    """One place, scanned for sale or to let the same way each time."""

    def __init__(
        self, scanner: ImmoScanner, country: str, area: Area, url: str = ""
    ) -> None:
        self.scanner = scanner
        self.country = country
        self.area = area
        self.url = url
        self.keep = split_list(area.source)
        self.drop = split_list(area.exclude_source)

    def scan(self, rent_or_buy: str, label: str = "") -> Listings:
        if self.url:
            results = self.scanner.research_real_estate_url(
                country_name=self.country, url=self.url
            )
        else:
            results = self.scanner.research_real_estate(
                country_name=self.country, rent_or_buy=rent_or_buy, **self.area.where()
            )

        scanned = sum(len(group) for group in results)
        results = self.scanner.filter_by_source(results, keep=self.keep, drop=self.drop)
        kept = sum(len(group) for group in results)

        findings = self.scanner.duplicate_finder(results)
        sources = f"{kept} from the asked sources, " if kept != scanned else ""
        print(f"{label}{scanned} listings, {sources}{len(findings)} unique")
        return findings


def report_brrrr(
    search: Search,
    findings: Listings,
    condition: str,
    works_per_m2: float,
    top: int,
) -> list[Row]:
    rentals = search.scan(RENT, label="to let: ")
    # a BRRRR hunt is for work to do; asking for "any" still means some
    condition = WORKS if condition in ("", ANY) else condition
    candidates = search.scanner.filter_by_condition(findings, condition)
    opportunities = Brrrr.rank(candidates, findings, rentals, works_per_m2=works_per_m2)
    print_areas(Brrrr.area_summary(findings, rentals))
    print_opportunities(opportunities, condition, top)
    return [opportunity_row(opportunity) for opportunity in opportunities]


def report_condition(
    scanner: ImmoScanner, findings: Listings, condition: str, top: int
) -> list[Row]:
    shown = scanner.filter_by_condition(findings, condition)
    if condition and condition != ANY:
        print(f"{len(shown)} of {len(findings)} need {condition}")
        print_listings(shown, top)
    return [item.to_dict() for item in shown]


def write_json(output: Path, rows: list[Row]) -> None:
    with Path(output).open("w", encoding="utf-8") as stream:
        json.dump(rows, stream, default=str, ensure_ascii=False, indent=2)
    print(f"written to {output}")


def split_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def print_insights(insights: Mapping[str, object]) -> None:
    for name, value in insights.items():
        if not isinstance(value, float):
            print(f"{name}: {value}")
        elif abs(value) < ROUNDING_THRESHOLD:
            print(f"{name}: {value:,.2f}")
        else:
            print(f"{name}: {value:,.0f}")


def describe(item: RealEstateResearchResult) -> str:
    epc = f" PEB {item.epc}" if item.epc else ""
    reasons = ", ".join(item.condition_reasons)
    return (
        f"{item.price_value:>9,.0f} {item.currency} "
        f"{item.livable_square_meters:>4} m² "
        f"{item.price_per_square_meter or 0:>6,.0f}/m²{epc} "
        f"{item.postal_code} {item.city}" + (f" [{reasons}]" if reasons else "")
    )


def print_listings(findings: Listings, top: int) -> None:
    cheapest = sorted(
        (item for item in findings if item.price_per_square_meter),
        key=lambda item: item.price_per_square_meter or 0,
    )
    for item in cheapest[:top]:
        print(f"  {describe(item)}")
        print(f"    {item.url}")


def print_areas(rows: Sequence[Row]) -> None:
    print("by postal code: median price/m², rent/m², gross yield, needing work")
    for row in rows:
        print(
            f"  {row['postal_code']} {row['city'][:18]:<18} "
            f"{row['median_price_per_m2']:>6,.0f}/m² "
            f"{row['median_rent_per_m2']:>6,.2f}/m² "
            f"{row['gross_yield_percent']:>5.1f}% "
            f"{row['needing_work']:>3}/{row['listings']}"
        )


def print_opportunities(
    opportunities: Sequence[Brrrr.Opportunity], condition: str, top: int
) -> None:
    print(
        f"{len(opportunities)} listings needing {condition}, "
        "best discount to their postal code first:"
    )
    for opportunity in opportunities[:top]:
        item = opportunity.item
        line = (
            f"  {opportunity.discount:>+6.0%} vs "
            f"{opportunity.reference_price_per_m2:,.0f}/m²  {describe(item)}"
        )
        print(line)
        details = (
            f"    after works ~{opportunity.after_repair_value:,.0f}, "
            f"equity {opportunity.equity:,.0f}"
        )
        if opportunity.monthly_rent:
            details += (
                f", rent ~{opportunity.monthly_rent:,.0f}/month, "
                f"{opportunity.gross_yield_percent:.1f}% gross on all-in cost"
            )
        if opportunity.notes:
            details += f" ({'; '.join(opportunity.notes)})"
        print(details)
        print(f"    {item.url}")


def opportunity_row(opportunity: Brrrr.Opportunity) -> Row:
    row = opportunity.item.to_dict()
    row.update(
        {
            "reference_scope": opportunity.reference_scope,
            "reference_price_per_m2": opportunity.reference_price_per_m2,
            "discount": opportunity.discount,
            "after_repair_value": opportunity.after_repair_value,
            "works_budget": opportunity.works_budget,
            "equity": opportunity.equity,
            "rent_per_m2": opportunity.rent_per_m2,
            "monthly_rent": opportunity.monthly_rent,
            "gross_yield_percent": opportunity.gross_yield_percent,
        }
    )
    return row


def print_report(report: Report) -> None:
    print(f"since the last run: {report.summary()}")

    for item in report.new[:10]:
        print(f"  new      {item.price_text or item.price} {item.city} {item.url}")

    for item, previous in report.price_changes[:10]:
        if previous is None:
            continue
        direction = "down" if float(item.price) < previous else "up  "
        print(
            f"  {direction}    {previous:,.0f} -> {float(item.price):,.0f} "
            f"{item.currency} {item.url}"
        )

    for row in report.gone[:10]:
        print(f"  gone     {row['price']} {row['city']} {row['url']}")


def cli() -> None:
    """Console-script entry point."""
    app.meta(sys.argv[1:])


if __name__ == "__main__":
    cli()
