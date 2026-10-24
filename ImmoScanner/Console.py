import json
import logging
import sys

import plac

from .Archives.Store import Store
from .ImmoScanner import ImmoScanner
from .Intellectuals import Brrrr
from .Intellectuals.Renovation import CONDITIONS, WORKS
from .Means.RealEstateResearch import ANY, BUY, PROPERTY_TYPES, RENT
from .Showrooms.Server import DEFAULT_PORT, serve


@plac.pos("country", "Country targeted by the research", type=str)
@plac.opt("postal_code", "postal code targeted by the research", type=str)
@plac.opt("city", "city targeted by the research", type=str)
@plac.opt("region", "province or canton to scan whole", type=str, abbrev="g")
@plac.opt("url", "url of targeted website", type=str)
@plac.opt("type", "property type", type=str, choices=PROPERTY_TYPES)
@plac.opt("output", "write the findings as JSON to this file", type=str)
@plac.opt("store", "sqlite archive to compare this run against", type=str)
@plac.opt(
    "source",
    "keep only listings from these originating portals, comma separated",
    type=str,
    abbrev="f",
)
@plac.opt(
    "exclude_source",
    "drop listings from these originating portals, comma separated",
    type=str,
    abbrev="x",
)
@plac.opt("max_pages", "result pages to walk per portal", type=int, abbrev="m")
@plac.opt("port", "port the explorer listens on", type=int, abbrev="n")
@plac.flg("serve_", "browse an archive instead of scanning", abbrev="w")
@plac.flg("rent", "search rentals instead of properties for sale")
@plac.flg("yield_", "scan for sale and to let, and report the gross rental yield")
@plac.opt(
    "condition",
    "keep listings needing at least this much work: works or renovate",
    type=str,
    choices=CONDITIONS,
    abbrev="k",
)
@plac.flg(
    "brrrr",
    "scan for sale and to let, and rank fixer-uppers against their postal code",
    abbrev="b",
)
@plac.opt(
    "works_per_m2", "renovation budget per m2 for --brrrr", type=float, abbrev="e"
)
@plac.opt("top", "how many listings to print", type=int, abbrev="l")
@plac.flg("debug", "Enable debug logging")
def main(
    country,
    postal_code="",
    city="",
    region="",
    url="",
    type=ANY,
    output="",
    store="",
    source="",
    exclude_source="",
    max_pages=0,
    port=DEFAULT_PORT,
    serve_=False,
    rent=False,
    yield_=False,
    condition=ANY,
    brrrr=False,
    works_per_m2=0.0,
    top=15,
    debug=False,
):
    """
    Welcome to ImmoScanner.
    Add at least either the postal code or the city; several postal codes can
    be given comma separated.
    If url is provided, only the targeted website will be parsed, country must still be provided.
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if serve_:
        if not store:
            sys.exit("--serve needs --store to say which archive to explore")
        return serve(store, port=port)

    scanner = ImmoScanner()

    if yield_:
        insights = scanner.research_gross_yield(
            country_name=country,
            postal_code=postal_code,
            city=city,
            region=region,
            type=type,
            max_pages=max_pages,
        )
        print_insights(insights)
        return

    if not (url or city or postal_code or region):
        sys.exit("provide one of --postal-code, --city, --region or --url")
    if brrrr and url:
        sys.exit("--brrrr compares a whole area: give a place rather than --url")

    def scan(rent_or_buy):
        if url:
            results = scanner.research_real_estate_url(country_name=country, url=url)
        else:
            results = scanner.research_real_estate(
                country_name=country,
                city=city,
                postal_code=postal_code,
                region=region,
                type=type,
                rent_or_buy=rent_or_buy,
                max_pages=max_pages,
            )

        scanned = sum(len(group) for group in results)
        results = scanner.filter_by_source(
            results, keep=split_list(source), drop=split_list(exclude_source)
        )
        kept = sum(len(group) for group in results)

        findings = scanner.duplicate_finder(results)
        side = "to let: " if rent_or_buy == RENT and brrrr else ""
        if kept != scanned:
            print(
                f"{side}{scanned} listings, {kept} from the asked sources, "
                f"{len(findings)} unique"
            )
        else:
            print(f"{side}{scanned} listings, {len(findings)} unique")
        return findings

    deal = RENT if rent and not brrrr else BUY
    findings = scan(deal)
    print_insights(scanner.get_insights(findings))

    if store:
        # the archive follows the whole market, whatever is shown below
        with Store(store) as archive:
            key = archive.search_key(country, region or postal_code or city, type, deal)
            print_report(archive.record(key, findings))

    if brrrr:
        rentals = scan(RENT)
        # a BRRRR hunt is for work to do; asking for "any" still means some
        condition = WORKS if condition in ("", ANY) else condition
        candidates = scanner.filter_by_condition(findings, condition)
        opportunities = Brrrr.rank(
            candidates, findings, rentals, works_per_m2=works_per_m2
        )
        print_areas(Brrrr.area_summary(findings, rentals))
        print_opportunities(opportunities, condition, top)
        rows = [opportunity_row(opportunity) for opportunity in opportunities]
    else:
        shown = scanner.filter_by_condition(findings, condition)
        if condition and condition != ANY:
            print(f"{len(shown)} of {len(findings)} need {condition}")
            print_listings(shown, top)
        rows = [item.to_dict() for item in shown]

    if output:
        with open(output, "w", encoding="utf-8") as stream:
            json.dump(rows, stream, default=str, ensure_ascii=False, indent=2)
        print(f"written to {output}")


def split_list(value):
    return [part.strip() for part in value.split(",") if part.strip()]


def print_insights(insights):
    for name, value in insights.items():
        if not isinstance(value, float):
            print(f"{name}: {value}")
        elif abs(value) < 100:  # yields and per-m2 rents lose all meaning rounded
            print(f"{name}: {value:,.2f}")
        else:
            print(f"{name}: {value:,.0f}")


def describe(item):
    epc = f" PEB {item.epc}" if item.epc else ""
    reasons = ", ".join(item.condition_reasons)
    return (
        f"{float(item.price):>9,.0f} {item.currency} "
        f"{item.livable_square_meters:>4} m² "
        f"{item.price_per_square_meter or 0:>6,.0f}/m²{epc} "
        f"{item.postal_code} {item.city}" + (f" [{reasons}]" if reasons else "")
    )


def print_listings(findings, top):
    cheapest = sorted(
        (item for item in findings if item.price_per_square_meter),
        key=lambda item: item.price_per_square_meter,
    )
    for item in cheapest[:top]:
        print(f"  {describe(item)}")
        print(f"    {item.url}")


def print_areas(rows):
    print("by postal code: median price/m², rent/m², gross yield, needing work")
    for row in rows:
        print(
            f"  {row['postal_code']} {row['city'][:18]:<18} "
            f"{row['median_price_per_m2']:>6,.0f}/m² "
            f"{row['median_rent_per_m2']:>6,.2f}/m² "
            f"{row['gross_yield_percent']:>5.1f}% "
            f"{row['needing_work']:>3}/{row['listings']}"
        )


def print_opportunities(opportunities, condition, top):
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


def opportunity_row(opportunity):
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


def print_report(report):
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


def cli():
    """Console-script entry point; plac parses argv for us."""
    plac.call(main)


if __name__ == "__main__":
    cli()
