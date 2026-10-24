"""Capture one result page per portal, and say what the readers made of it.

Run where the portals can be reached (the capture workflow does, on GitHub):

    uv run python scripts/capture_portals.py captures/

For each portal it saves the raw page or JSON as it came back, then reads it
with the portal's own reader, and writes ``summary.json``: which download rung
answered, whether an anti-bot wall was served, how many listings came out, and
a couple of them in full. A reader that comes back empty on a real page is
fixed against that page; a portal that only ever serves a wall is dropped.
"""

import json
import logging
import sys
from pathlib import Path

from ImmoScanner.Means.RealEstateResearch import ANY, APARTMENT, RealEstateResearch
from ImmoScanner.Workers.BienIci import BienIci
from ImmoScanner.Workers.ImmoScout24 import ImmoScout24
from ImmoScanner.Workers.Immowelt import Immowelt
from ImmoScanner.Workers.Kleinanzeigen import Kleinanzeigen
from ImmoScanner.Workers.Leboncoin import Leboncoin
from ImmoScanner.Workers.Pap import Pap
from ImmoScanner.Workers.RealEstateWorker import BOT_WALL_MARKERS
from ImmoScanner.Workers.SeLoger import SeLoger

LYON = {"postal_code": "69001", "city": "Lyon", "type": ANY}
BERLIN = {"postal_code": "10115", "city": "Berlin", "type": APARTMENT}
BERLIN_ANY = {"postal_code": "10115", "city": "Berlin", "type": ANY}

#: one search per portal: a place where the portal can search one, else a
#: search url as the site itself builds it for a big city
SEARCHES = [
    (BienIci, LYON),
    (Leboncoin, LYON),
    (SeLoger, {"url": "https://www.seloger.com/immobilier/achat/immo-lyon-69/"}),
    (Pap, {"url": "https://www.pap.fr/annonce/vente-immobiliere-lyon-69-g43590"}),
    (Kleinanzeigen, BERLIN),
    (
        ImmoScout24,
        {
            "url": "https://www.immobilienscout24.de/Suche/de/berlin/berlin/wohnung-kaufen"
        },
    ),
    (Immowelt, BERLIN_ANY),
]
SAMPLES = 2


def capture(worker_class, terms, folder):
    worker = worker_class()
    worker.MAX_PAGES = 1
    research = RealEstateResearch(**terms)
    record = {"portal": worker.domain_name, "terms": terms}

    try:
        worker.fill_empty_fields(research)
        url = worker.url_builder(research, 1)
        record["url"] = url
        raw = worker.get_html(url, worker.WAIT_FOR)
    except Exception as error:  # noqa: BLE001 - every failure is the finding
        record["error"] = f"{type(error).__name__}: {error}"
        return record
    finally:
        record["zones"] = getattr(worker, "zones", None)

    suffix = ".json" if raw.lstrip().startswith(("{", "[")) else ".html"
    (folder / f"{worker.domain_name}{suffix}").write_text(raw, encoding="utf-8")
    record["bytes"] = len(raw)
    record["rung"] = worker.http_client or "browser"
    record["bot_wall"] = [marker for marker in BOT_WALL_MARKERS if marker in raw]

    # Read the captured page, not a second download of it.
    worker.get_html = lambda *_args, **_kwargs: raw
    try:
        findings = worker.get_findings(research)
    except Exception as error:  # noqa: BLE001
        record["read_error"] = f"{type(error).__name__}: {error}"
        findings = []
    finally:
        worker.close()

    record["listings"] = len(findings)
    record["priced"] = sum(1 for item in findings if item.price)
    record["measured"] = sum(1 for item in findings if item.livable_square_meters)
    record["samples"] = [item.to_dict() for item in findings[:SAMPLES]]
    return record


def main(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    summary = [capture(worker, terms, folder) for worker, terms in SEARCHES]
    (folder / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    for record in summary:
        outcome = (
            record.get("error")
            or record.get("read_error")
            or (
                f"{record['listings']} listings, {record['priced']} priced, "
                f"{record['measured']} measured, wall: {record['bot_wall'] or 'none'}"
            )
        )
        print(f"{record['portal']:<22} {outcome}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "captures")
