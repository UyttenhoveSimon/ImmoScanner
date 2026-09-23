"""Live checks against the real portals - the canary for a portal redesign.

Excluded from the default run (they need the network and a browser). The
scheduled CI job runs them with ``pytest -m live``: a portal that silently
changes its markup shows up as an empty result set here, days before a scan
quietly returns nothing.
"""

import pytest

from ImmoScanner.Means.RealEstateResearch import ANY, BUY, RealEstateResearch
from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb

pytestmark = pytest.mark.live

SEARCHES = [
    (Immoweb, "5000", "Namur"),
    (ImmoVlan, "5000", "Namur"),
    (Comparis, "1618", "Châtel-St-Denis"),
]


@pytest.mark.parametrize(
    "worker_class, postal_code, city", SEARCHES, ids=lambda value: str(value)
)
def test_the_portal_still_yields_usable_listings(worker_class, postal_code, city):
    worker = worker_class()
    worker.MAX_PAGES = 1  # one page is enough to prove the extractors still bite

    results = worker.get_findings(
        RealEstateResearch(
            postal_code=postal_code, city=city, type=ANY, rent_or_buy=BUY
        )
    )

    assert results, f"{worker.domain_name} returned no listing at all"
    assert all(item.id for item in results), f"{worker.domain_name} lost its ids"
    assert all(item.url.startswith("http") for item in results)

    # New-build developments carry a price range instead of a price; immoweb
    # sorts a page full of them first, so they are not evidence of a break.
    properties = [item for item in results if not item.is_project]
    assert properties, f"{worker.domain_name} returned only project listings"

    priced = [item for item in properties if item.price]
    measured = [item for item in properties if item.livable_square_meters]

    # A redesign usually keeps the cards and breaks the fields inside them.
    assert len(priced) > len(properties) / 2, f"{worker.domain_name} lost its prices"
    assert (
        len(measured) > len(properties) / 2
    ), f"{worker.domain_name} lost its surfaces"
