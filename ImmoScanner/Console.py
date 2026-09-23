import json
import logging
import sys

import plac

from .Archives.Store import Store
from .ImmoScanner import ImmoScanner
from .Means.RealEstateResearch import ANY, BUY, PROPERTY_TYPES, RENT


@plac.pos("country", "Country targeted by the research", type=str)
@plac.opt("postal_code", "postal code targeted by the research", type=str)
@plac.opt("city", "city targeted by the research", type=str)
@plac.opt("url", "url of targeted website", type=str)
@plac.opt("type", "property type", type=str, choices=PROPERTY_TYPES)
@plac.opt("output", "write the findings as JSON to this file", type=str)
@plac.opt("store", "sqlite archive to compare this run against", type=str)
@plac.flg("rent", "search rentals instead of properties for sale")
@plac.flg("yield_", "scan for sale and to let, and report the gross rental yield")
@plac.flg("debug", "Enable debug logging")
def main(
    country,
    postal_code="",
    city="",
    url="",
    type=ANY,
    output="",
    store="",
    rent=False,
    yield_=False,
    debug=False,
):
    """
    Welcome to ImmoScanner.
    Add at least either the postal code or the city.
    If url is provided, only the targeted website will be parsed, country must still be provided.
    """
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    scanner = ImmoScanner()

    if yield_:
        insights = scanner.research_gross_yield(
            country_name=country, postal_code=postal_code, city=city, type=type
        )
        print_insights(insights)
        return

    if url:
        results = scanner.research_real_estate_url(country_name=country, url=url)
    elif city or postal_code:
        results = scanner.research_real_estate(
            country_name=country,
            city=city,
            postal_code=postal_code,
            type=type,
            rent_or_buy=RENT if rent else BUY,
        )
    else:
        sys.exit("provide either --postal-code, --city or --url")

    findings = scanner.duplicate_finder(results)
    print(f"{sum(len(group) for group in results)} listings, {len(findings)} unique")

    print_insights(scanner.get_insights(findings))

    if store:
        with Store(store) as archive:
            key = archive.search_key(
                country, postal_code or city, type, RENT if rent else BUY
            )
            print_report(archive.record(key, findings))

    if output:
        with open(output, "w", encoding="utf-8") as stream:
            json.dump(
                [item.to_dict() for item in findings],
                stream,
                default=str,
                ensure_ascii=False,
                indent=2,
            )
        print(f"written to {output}")


def print_insights(insights):
    for name, value in insights.items():
        if not isinstance(value, float):
            print(f"{name}: {value}")
        elif abs(value) < 100:  # yields and per-m2 rents lose all meaning rounded
            print(f"{name}: {value:,.2f}")
        else:
            print(f"{name}: {value:,.0f}")


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
