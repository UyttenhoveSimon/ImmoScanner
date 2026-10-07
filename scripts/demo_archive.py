"""Build a demo archive of made-up listings, to try the explorer without scanning.

    uv run python scripts/demo_archive.py
    uv run immoscanner Belgium --serve --store demo.db

Every listing is invented: no portal's text, no real address, no live url. The
archive holds four weekly scans, so new listings, price cuts and withdrawals all
show up the way they would after a month of real use.
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ImmoScanner.Archives.Store import Store
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult

# country, postal code, town, centre, currency, sale price per m², rent per m²
PLACES = [
    ("Belgium", "1300", "Wavre", (50.717, 4.601), "EUR", 2900, 12.5),
    ("Belgium", "1400", "Nivelles", (50.598, 4.328), "EUR", 2450, 12.0),
    ("Belgium", "1410", "Waterloo", (50.715, 4.399), "EUR", 3400, 13.5),
    ("Belgium", "1420", "Braine-l'Alleud", (50.683, 4.368), "EUR", 2850, 12.5),
    ("Belgium", "5000", "Namur", (50.467, 4.867), "EUR", 2300, 11.5),
    ("Switzerland", "1003", "Lausanne", (46.520, 6.633), "CHF", 11000, 33.0),
    ("Switzerland", "1618", "Châtel-Saint-Denis", (46.527, 6.900), "CHF", 7200, 22.0),
]

PORTALS = {"EUR": ["immoweb.be", "immovlan.be"], "CHF": ["comparis.ch"]}
SOURCES = ["homegate.ch", "immoscout24.ch", "comparis.ch"]

SCANS = 4
FIRST_SCAN = datetime(2026, 9, 9, 9, 0, tzinfo=timezone.utc)


def listing(rng, number, place, deal):
    country, postal_code, town, (lat, lon), currency, sale_m2, rent_m2 = place
    kind = rng.choice(["House", "Apartment"])
    surface = rng.randint(90, 260) if kind == "House" else rng.randint(40, 140)
    if deal == "rent":
        surface = int(surface * 0.75)
    bedrooms = max(1, surface // 45)
    platform = rng.choice(PORTALS[currency])

    result = RealEstateResearchResult()
    result.id = f"demo-{number}"
    result.platform = platform
    result.source = rng.choice(SOURCES) if platform == "comparis.ch" else ""
    result.url = f"https://example.com/demo/{number}"
    result.description = f"{bedrooms}-bedroom {kind.lower()} in {town} (demo)"
    result.type = kind
    result.postal_code = postal_code
    result.city = town
    result.currency = currency
    result.livable_square_meters = surface
    result.bedrooms_number = bedrooms
    if deal == "buy":
        result.price = round(surface * sale_m2 * rng.uniform(0.75, 1.3), -4)
    else:
        result.price = round(surface * rent_m2 * rng.uniform(0.8, 1.25), -1)
    # Only the portals that geocode get a position, as in a real scan.
    if platform != "immovlan.be":
        result.latitude = lat + rng.uniform(-0.02, 0.02)
        result.longitude = lon + rng.uniform(-0.03, 0.03)
    return result


def build(path):
    rng = random.Random(42)
    Path(path).unlink(missing_ok=True)
    numbers = iter(range(100000, 1000000))

    with Store(path) as archive:
        for place in PLACES:
            for deal in ("buy", "rent"):
                key = archive.search_key(place[0], place[1], "any", deal)
                market = [
                    listing(rng, next(numbers), place, deal)
                    for _ in range(rng.randint(40, 90))
                ]

                for week in range(SCANS):
                    if week:
                        # A week on the market: some sell, some get cheaper, some arrive.
                        market = [item for item in market if rng.random() > 0.08]
                        for item in market:
                            if rng.random() < 0.07:
                                cut = 0.97 if deal == "buy" else 0.95
                                item.price = round(item.price * cut, -3 if deal == "buy" else 1)
                        market += [
                            listing(rng, next(numbers), place, deal)
                            for _ in range(rng.randint(2, 8))
                        ]

                    seen_at = (FIRST_SCAN + timedelta(weeks=week)).isoformat()
                    archive.record(key, market, seen_at=seen_at)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "demo.db"
    build(target)
    print(f"demo archive written to {target}")
