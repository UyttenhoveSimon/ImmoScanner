# AGENTS.md

Guidance for AI coding agents (and humans in a hurry) working in this
repository. Read this first; the README is the user-facing documentation.

## What this is

ImmoScanner reads real estate portals for a place in Belgium, Switzerland,
France or Germany, de-duplicates the listings across portals, computes price
statistics, rental yields and a BRRRR ranking of fixer-uppers, keeps every scan
in a SQLite archive, and serves a web explorer over that archive.

Python 3.10+, managed with **uv**. The CLI is **cyclopts**; pages are fetched
over plain HTTP, then `curl_cffi`, then a headless browser (**rustwright**).

## Commands

```bash
uv sync                                  # install everything, dev tools included
uv run pytest                            # offline test suite (~400 tests, ~12 s)
uv run pytest --cov                      # with coverage; CI requires >= 95 %
uv run pytest -m live                    # against the real portals (network)
uv run prek run --all-files              # every check CI runs: ruff, ty, uv-lock, whitespace
uv run ruff check --fix . && uv run ruff format .
uv run ty check                          # type check
uv run immoscanner --help                # scan | yield | brrrr | serve
```

Run `uv run prek run --all-files` before every commit. It only checks files
git tracks: `git add` new files first, or CI will catch what you did not.

## Map

```
ImmoScanner/
  Console.py            cyclopts app: scan, yield, brrrr, serve; --debug on the meta app
  ImmoScanner.py        a scan: locate the place, ask each portal in a thread, de-duplicate
  Countries/            one class per country: its portals, régions, geonames lookups
  Workers/              one class per portal
    Worker.py           the fetching ladder (requests -> curl_cffi -> browser)
    RealEstateWorker.py page walk, bot-wall detection, shared helpers, capability flags
    SchemaOrg.py        reader for portals publishing JSON-LD
    Aviv.py             reader for the AVIV group's cards (immowelt, seloger)
  Means/                RealEstateResearch (the question), RealEstateResearchResult (a listing)
  Intellectuals/        StatisticalInsights, Renovation (condition from text + EPC), Brrrr (ranking)
  Archives/Store.py     SQLite archive and the diff between runs
  Showrooms/            the web explorer (Server, Explorer queries, Runner for scans started there)
scripts/                demo archive, portal capture, discount scan
tests/                  offline tests; fixtures/ holds trimmed pages captured from the portals
.github/workflows/      tests, live canary, portal capture, area scan
```

## Rules of this repository

- **Never hit the network in unit tests.** Portals, geonames, HTTP clients and
  the browser are replaced by fixtures or fakes. Live checks go in
  `tests/test_live_portals.py`, marked `live`.
- **Fixtures are real captures, trimmed** to a few listings. A payload written
  by hand must say it is synthetic, in the test module's docstring.
- **A portal reader is `VERIFIED = False` until it has been checked on a
  captured page.** Unverified portals warn in the log and are expected
  failures (`xfail`) in the live tests. Flip the flag in the same commit that
  adds the real fixture.
- **Anti-bot walls are reported, never bypassed.** Recognise a new wall by
  adding a marker to `BOT_WALL_MARKERS`; do not add evasion.
- **Ruff runs with `select = ["ALL"]`.** Fix what it finds; an ignore needs a
  reason, in `pyproject.toml` or on the `noqa` line.
- **Type annotations are required** in `Means/`, `Intellectuals/`,
  `ImmoScanner.py` and `Console.py`; ty checks the whole tree.
- **Comments say why, not what.** Docstrings explain the portal quirk or the
  decision behind the code; keep that voice.
- Commit messages: a short imperative subject, then a body saying why.

## Adding a portal

1. Subclass `RealEstateWorker` (or `SchemaOrgWorker` / `AvivWorker` when the
   portal fits) in `ImmoScanner/Workers/`. Fill `url_builder`, `extract_findings`
   and the selectors; override `fetch_page` only if listings are not in the HTML.
2. Declare what it can do: `SEARCH_BY_PLACE`, `SEARCH_BY_REGION`, `VERIFIED`.
3. Register it in its country under `Countries/`.
4. Capture a real page: run the **portal capture** workflow (pages land on the
   `portal-captures` branch) or `uv run python scripts/capture_portals.py out/`.
5. Trim the capture into `tests/fixtures/`, test against it, then set
   `VERIFIED = True`.

## Pitfalls already met

- Portals change markup silently: a scan then returns *fewer* listings, not an
  error. That is what the live canary and the capture workflow are for.
- Kleinanzeigen ignores a postal code in the URL path and searches all of
  Germany; it is searched through its form, then paged from the canonical URL.
- Prices can be `None` ("on request"): use `item.price_value`, never
  `float(item.price)`.
- plac is gone; cyclopts builds the CLI from type annotations, so a parameter's
  annotation *is* its CLI type.
- This repository is public: anything a workflow publishes on a branch
  (captures, scan results) is public too.
