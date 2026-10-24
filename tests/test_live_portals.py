"""Live checks against the real portals - the canary for a portal redesign.

Excluded from the default run (they need the network and a browser). The
scheduled CI job runs them with ``pytest -m live``: a portal that silently
changes its markup shows up as an empty result set here, days before a scan
quietly returns nothing.
"""

import pytest

from ImmoScanner.Means.RealEstateResearch import ANY, BUY, RealEstateResearch
from ImmoScanner.Workers.BienIci import BienIci
from ImmoScanner.Workers.Comparis import Comparis
from ImmoScanner.Workers.ImmoScout24 import ImmoScout24
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb
from ImmoScanner.Workers.Immowelt import Immowelt
from ImmoScanner.Workers.Kleinanzeigen import Kleinanzeigen
from ImmoScanner.Workers.Leboncoin import Leboncoin
from ImmoScanner.Workers.Pap import Pap
from ImmoScanner.Workers.SeLoger import SeLoger

pytestmark = pytest.mark.live

#: a reader written before its portal could be captured is expected to fail
#: until it is checked; the run reports XPASS the day it starts working
UNVERIFIED = pytest.mark.xfail(reason="reader not yet checked on the live site")

SEARCHES = [
    (Immoweb, {"postal_code": "5000", "city": "Namur"}),
    (ImmoVlan, {"postal_code": "5000", "city": "Namur"}),
    (Comparis, {"postal_code": "1618", "city": "Châtel-St-Denis"}),
    pytest.param(BienIci, {"postal_code": "69001", "city": "Lyon"}, marks=UNVERIFIED),
    pytest.param(Leboncoin, {"postal_code": "69001", "city": "Lyon"}, marks=UNVERIFIED),
    pytest.param(
        SeLoger,
        {"url": "https://www.seloger.com/immobilier/achat/immo-lyon-69/"},
        marks=UNVERIFIED,
    ),
    pytest.param(
        Pap,
        {"url": "https://www.pap.fr/annonce/vente-immobiliere-lyon-69-g43590"},
        marks=UNVERIFIED,
    ),
    pytest.param(
        Kleinanzeigen, {"postal_code": "10115", "city": "Berlin"}, marks=UNVERIFIED
    ),
    pytest.param(
        ImmoScout24,
        {
            "url": "https://www.immobilienscout24.de/Suche/de/berlin/berlin/wohnung-kaufen"
        },
        marks=UNVERIFIED,
    ),
    pytest.param(Immowelt, {"city": "Berlin"}, marks=UNVERIFIED),
]


@pytest.mark.parametrize(
    ("worker_class", "terms"),
    SEARCHES,
    ids=lambda value: getattr(value, "__name__", ""),
)
def test_the_portal_still_yields_usable_listings(worker_class, terms):
    worker = worker_class()
    worker.MAX_PAGES = 1  # one page is enough to prove the extractors still bite

    results = worker.get_findings(
        RealEstateResearch(type=ANY, rent_or_buy=BUY, **terms)
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
    assert len(measured) > len(properties) / 2, (
        f"{worker.domain_name} lost its surfaces"
    )
