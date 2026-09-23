# ImmoScanner

Scans real estate portals for a city or postal code, reports price statistics,
and tells you what changed since the last run.

Browser automation runs on [rustwright](https://github.com/Skyvern-AI/rustwright),
a Rust rewrite of Playwright with a drop-in `sync_api`: no Node driver process,
and it reuses any Chromium already on the machine. Most portals never need it -
their result lists are server-rendered, so a plain HTTP GET is tried first and
the browser only starts when that comes back incomplete.

## Install

```bash
uv sync
uv run python -m rustwright install chromium
```

## Use

```bash
uv run immoscanner Belgium --city Namur
uv run immoscanner Belgium --postal-code 1000 --type apartment --rent
uv run immoscanner Switzerland --postal-code 1618 --output ch.json
uv run immoscanner Belgium --postal-code 1000 --type apartment --yield
uv run immoscanner Belgium --city Namur --store namur.db
uv run immoscanner Belgium --url "https://www.immoweb.be/fr/recherche/maison/a-vendre/namur/5000?countries=BE"
```

| flag | effect |
| --- | --- |
| `--type any\|house\|apartment` | property type, mapped onto each portal's own vocabulary |
| `--rent` | rentals instead of properties for sale |
| `--yield` | scan for sale *and* to let, and report the gross rental yield |
| `--store FILE.db` | archive the run and report what is new, repriced or gone |
| `--output FILE.json` | write the de-duplicated listings |
| `IMMOSCANNER_BROWSER_PATH` | point the engine at a specific Chromium build |

## Portal status

| Portal | Country | State |
| --- | --- | --- |
| immoweb.be | BE | works — listing JSON embedded in the server-rendered cards |
| immovlan.be | BE | works — moved off `immo.vlan.be`, which now 503s |
| comparis.ch | CH | works — `__NEXT_DATA__` payload; needs the browser, it refuses plain HTTP |

homegate.ch and immoscout24.ch are behind DataDome on every entry point, their
APIs included, so they have no worker. Their listings still show up: comparis
aggregates both, and each result names its originating portal in `source`.

New-build developments are advertised as a price *range* over a whole building.
They are reported with `is_project`, `price_min` and `price_max`, and left out
of the statistics rather than averaged into them.

## Tests

```bash
uv run pytest            # offline, against search pages captured in tests/fixtures
uv run pytest -m live    # hits the real portals; run weekly in CI as a canary
```

The offline suite is what catches a portal redesign: it asserts on the exact
selectors and payload keys the workers depend on. When a portal changes for
good, recapture its fixture.
