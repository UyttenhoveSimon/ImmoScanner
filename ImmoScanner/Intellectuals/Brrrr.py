"""Rank fixer-uppers the way a BRRRR investor reads them.

Buy, Rehab, Rent, Refinance, Repeat works when a property bought below its
neighbourhood's price, then brought up to its standard, is worth enough to
refinance most of what went into it, and lets for enough to carry the loan.

So each candidate is measured against its own postal code:

* the reference price per m² is the median of the listings there that show
  no sign of needing work - the closest thing a search page has to an
  after-repair value. Too few of those, and every listing of the postal code
  stands in; too few of those, and the whole scan does.
* the rent per m² is the median of what is to let in the same postal code,
  when rentals were scanned, with the same fallback.

The figures are asking prices, not sales, and the renovation budget is a flat
cost per m²: a first sort through a few hundred listings, not a valuation.
"""

import statistics
from dataclasses import dataclass, field

from .Renovation import RANK
from .StatisticalInsights import StatisticalInsights

#: below this many comparables a median says more about one house than an area
MIN_COMPARABLES = 5
POSTAL_CODE, POSTAL_CODE_ALL, SCAN = "postal code", "postal code, all", "scan"


@dataclass
class Opportunity:
    item: object
    #: where the reference price came from: one of the three scopes above
    reference_scope: str
    reference_price_per_m2: float
    #: how far under the reference the asking price is, as a fraction
    discount: float
    after_repair_value: float
    works_budget: float
    #: what is left once bought and renovated: the margin a refinance draws on
    equity: float
    rent_per_m2: float = 0
    monthly_rent: float = 0
    #: yearly rent over purchase price plus works, in percent
    gross_yield_percent: float = 0
    notes: list = field(default_factory=list)

    @property
    def all_in_cost(self):
        return float(self.item.price) + self.works_budget


def median_per_m2(listings):
    return StatisticalInsights(listings).price_per_square_meter_median()


class Reference:
    """Median price per m², postal code by postal code, with fallbacks."""

    def __init__(self, listings, prefer=lambda item: True):
        self.listings = [
            item
            for item in listings
            if not item.is_project and item.price_per_square_meter
        ]
        self.prefer = prefer
        self.cache = {}

    def for_postal_code(self, postal_code):
        if postal_code not in self.cache:
            local = [i for i in self.listings if i.postal_code == postal_code]
            preferred = [i for i in local if self.prefer(i)]
            if len(preferred) >= MIN_COMPARABLES:
                found = (POSTAL_CODE, median_per_m2(preferred))
            elif len(local) >= MIN_COMPARABLES:
                found = (POSTAL_CODE_ALL, median_per_m2(local))
            else:
                everywhere = [i for i in self.listings if self.prefer(i)]
                found = (SCAN, median_per_m2(everywhere or self.listings))
            self.cache[postal_code] = found
        return self.cache[postal_code]


def needs_no_work(item):
    return RANK[item.condition] == 0


def rank(candidates, market, rentals=(), works_per_m2=0):
    """Measure each candidate against its area; best discount first.

    ``market`` is the whole sale scan the candidates were picked from: it sets
    what a renovated property is worth. ``rentals`` sets the rent.
    """
    prices = Reference(market, prefer=needs_no_work)
    rents = Reference(rentals)
    opportunities = []

    for item in candidates:
        if item.is_project or not item.price_per_square_meter:
            continue

        scope, reference = prices.for_postal_code(item.postal_code)
        if not reference:
            continue

        surface = item.livable_square_meters
        works = works_per_m2 * surface
        after_repair_value = reference * surface
        opportunity = Opportunity(
            item=item,
            reference_scope=scope,
            reference_price_per_m2=reference,
            discount=1 - item.price_per_square_meter / reference,
            after_repair_value=after_repair_value,
            works_budget=works,
            equity=after_repair_value - float(item.price) - works,
        )
        if scope != POSTAL_CODE:
            opportunity.notes.append(f"reference: {scope}")

        if rents.listings:
            rent_scope, rent_per_m2 = rents.for_postal_code(item.postal_code)
            opportunity.rent_per_m2 = rent_per_m2
            opportunity.monthly_rent = rent_per_m2 * surface
            opportunity.gross_yield_percent = StatisticalInsights.gross_yield(
                opportunity.monthly_rent, opportunity.all_in_cost
            )
            if rent_scope != POSTAL_CODE:
                opportunity.notes.append(f"rent: {rent_scope}")

        opportunities.append(opportunity)

    return sorted(opportunities, key=lambda o: o.discount, reverse=True)


def area_summary(market, rentals=()):
    """Price and rent per m² of every postal code scanned, for picking areas."""
    rows = []
    for postal_code in sorted({item.postal_code for item in market}):
        local = [i for i in market if i.postal_code == postal_code]
        let = [i for i in rentals if i.postal_code == postal_code]
        price_per_m2 = median_per_m2([i for i in local if not i.is_project])
        rent_per_m2 = median_per_m2(let)
        rows.append(
            {
                "postal_code": postal_code,
                "city": statistics.mode([i.city for i in local]) if local else "",
                "listings": len(local),
                "needing_work": sum(1 for i in local if not needs_no_work(i)),
                "median_price_per_m2": price_per_m2,
                "rentals": len(let),
                "median_rent_per_m2": rent_per_m2,
                "gross_yield_percent": (
                    rent_per_m2 * 12 / price_per_m2 * 100 if price_per_m2 else 0
                ),
            }
        )
    return rows
