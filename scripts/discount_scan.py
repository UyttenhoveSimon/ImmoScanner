"""Rank every listing of an area by how far under its postal code it is priced.

    uv run python scripts/discount_scan.py Switzerland 1618,1630 --type apartment

Unlike ``immoscanner brrrr``, which only ranks listings that need work, this
ranks them all: a listing far under the median price per m2 of the listings
around it that need no work is either a bargain or a story (a ruin, a life
annuity, a share of a building, a mistake in the surface) worth reading.

Writes ``results.md`` (the area table and the ranked listings) and
``results.json`` (every listing with its figures) to the output folder.
"""

import argparse
import json
import logging
from pathlib import Path

from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Intellectuals import Brrrr
from ImmoScanner.Means.RealEstateResearch import BUY, RENT

TOP = 30


def markdown(country, codes, kind, areas, opportunities, top):
    lines = [
        f"# Listings priced under their postal code — {country}, {kind}",
        "",
        f"Postal codes: {', '.join(codes)}",
        "",
        "## By postal code",
        "",
        (
            "| Postal code | Town | For sale | Needing work | Median price/m² "
            "| Median rent/m² | Gross yield |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines += [
        f"| {row['postal_code']} | {row['city']} | {row['listings']} "
        f"| {row['needing_work']} | {row['median_price_per_m2']:,.0f} "
        f"| {row['median_rent_per_m2']:,.2f} | {row['gross_yield_percent']:.1f}% |"
        for row in areas
    ]
    lines += [
        "",
        f"## The {min(top, len(opportunities))} deepest discounts",
        "",
        (
            "Discount: asking price per m² against the median of the listings in the "
            "same postal code that show no sign of needing work."
        ),
        "",
        (
            "| # | Discount | Price | m² | Price/m² | Reference/m² | Rooms "
            "| Place | Condition | Rent/month | Gross yield | Listing |"
        ),
        (
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: "
            "| ---: | --- |"
        ),
    ]
    for rank, opportunity in enumerate(opportunities[:top], start=1):
        item = opportunity.item
        condition = ", ".join(item.condition_reasons) or "-"
        note = f" ({'; '.join(opportunity.notes)})" if opportunity.notes else ""
        lines.append(
            f"| {rank} | {opportunity.discount:+.0%} | {item.price_value:,.0f} "
            f"| {item.livable_square_meters} | {item.price_per_square_meter or 0:,.0f} "
            f"| {opportunity.reference_price_per_m2:,.0f}{note} "
            f"| {item.rooms_number or '-'} | {item.postal_code} {item.city} "
            f"| {condition} | {opportunity.monthly_rent:,.0f} "
            f"| {opportunity.gross_yield_percent:.1f}% "
            f"| [{(item.description or 'listing')[:50]}]({item.url}) |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("country")
    parser.add_argument("postal_codes", help="comma separated")
    parser.add_argument("--type", default="any", choices=("any", "house", "apartment"))
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--top", type=int, default=TOP)
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    codes = [code.strip() for code in args.postal_codes.split(",") if code.strip()]
    scanner = ImmoScanner()
    sides = {}
    for deal in (BUY, RENT):
        sides[deal] = scanner.duplicate_finder(
            scanner.research_real_estate(
                args.country,
                postal_code=",".join(codes),
                type=args.type,
                rent_or_buy=deal,
                max_pages=args.max_pages,
            )
        )
    selling, renting = sides[BUY], sides[RENT]

    opportunities = Brrrr.rank(selling, selling, renting)
    areas = Brrrr.area_summary(selling, renting)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.md").write_text(
        markdown(args.country, codes, args.type, areas, opportunities, args.top),
        encoding="utf-8",
    )
    rows = []
    for opportunity in opportunities:
        row = opportunity.item.to_dict()
        row.update(
            discount=opportunity.discount,
            reference_price_per_m2=opportunity.reference_price_per_m2,
            reference_scope=opportunity.reference_scope,
            monthly_rent=opportunity.monthly_rent,
            gross_yield_percent=opportunity.gross_yield_percent,
        )
        rows.append(row)
    (out / "results.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"{len(selling)} for sale, {len(renting)} to let, written to {out}")


if __name__ == "__main__":
    main()
