# ImmoScanner

Scans real estate portals for a city or postal code, reports price statistics,
and tells you what changed since the last run.

```bash
uv sync
uv run python -m rustwright install chromium
uv run immoscanner Belgium --city Namur
```

## Use

The first positional argument is the country; give it a city, a postal code, or
a portal search url.

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
| `--city NAME` / `--postal-code CODE` | either one is enough; the other is looked up |
| `--type any\|house\|apartment` | property type, mapped onto each portal's own vocabulary |
| `--rent` | rentals instead of properties for sale |
| `--yield` | scan for sale *and* to let, and report the gross rental yield |
| `--store FILE.db` | archive the run and report what is new, repriced or gone |
| `--source NAMES` | keep only these originating portals, comma separated |
| `--exclude-source NAMES` | drop these originating portals, comma separated |
| `--output FILE.json` | write the de-duplicated listings |
| `--url URL` | scan one portal's own search url, paginating it |
| `--debug` | per-card logging |

`IMMOSCANNER_BROWSER_PATH` points the engine at a specific Chromium build.

### What a run prints

```
$ uv run immoscanner Belgium --postal-code 5000 --type house --store namur.db
INFO ImmoScanner.ImmoScanner: searching Namur (5000) in Belgium
INFO ImmoScanner.Workers.RealEstateWorker: immovlan.be: 30 listings
INFO ImmoScanner.Workers.RealEstateWorker: immoweb.be: 129 listings
159 listings, 117 unique
listings: 111
projects: 6
mean_price: 443,521
median_price: 395,000
median_price_per_m2: 1,923
since the last run: 117 new, 0 repriced, 0 gone, 0 unchanged
  new      950 000 Namur https://immovlan.be/fr/detail/maison/a-vendre/5000/namur/vbe67521
  ...
```

`159 listings, 117 unique` is what the portals returned against what survived
de-duplication. `listings` and `projects` split the unique set into comparable
properties and new-build developments; only the former feed the statistics.

Run it again later against the same archive and only the difference shows:

```
since the last run: 0 new, 2 repriced, 1 gone, 114 unchanged
  down    395,000 -> 379,000 € https://www.immoweb.be/fr/annonce/...
  gone    289000.0 Namur https://immovlan.be/fr/detail/...
```

`--yield` scans the area twice and adds the rental side:

```
$ uv run immoscanner Switzerland --postal-code 1003 --type apartment --yield
median_price_per_m2: 11,033
rental_median_price: 2,500
rental_median_price_per_m2: 33.36
gross_yield_percent: 2.04
```

### What `--output` writes

One json object per de-duplicated listing:

```json
{
  "url": "https://www.immoweb.be/fr/annonce/maison/a-vendre/namur/5000/21841479",
  "id": "21841479",
  "platform": "immoweb.be",
  "source": "",
  "description": "MAISON DE CARACTÈRE DE 224 M² À RÉINVENTER À BEEZ",
  "type": "House",
  "price": 369000,
  "price_text": "369 000 €",
  "currency": "EUR",
  "postal_code": "5000",
  "city": "Namur",
  "livable_square_meters": 294,
  "bedrooms_number": 5,
  "rooms_number": 0,
  "latitude": 50.4666968,
  "longitude": 4.915161299999999,
  "posted_date": "2026-09-16T13:04:43.191Z",
  "is_project": false,
  "price_min": 0,
  "price_max": 0
}
```

`source` is filled when the portal is an aggregator: comparis names the site it
took the listing from, which is what `--source` and `--exclude-source` match on
(case-insensitive substring; a portal that publishes its own listings is its own
origin). Filtering happens before de-duplication, so asking for one origin picks
that copy rather than whichever copy happened to survive.

```
$ uv run immoscanner Switzerland --postal-code 1003 --type apartment --rent --source homegate
102 listings, 13 from the asked sources, 11 unique
```
 `price` is `0` on a development, which instead carries
`price_min` and `price_max`. `latitude` and `longitude` are present only for the
portals that geocode.

### As a library

```python
from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Means.RealEstateResearch import APARTMENT, RENT

scanner = ImmoScanner()
results = scanner.research_real_estate("Belgium", postal_code="1000",
                                       type=APARTMENT, rent_or_buy=RENT)
listings = scanner.duplicate_finder(results)
insights = scanner.get_insights(listings)
```

### Being a good guest

A scan walks at most 20 pages per portal and pauses 800 ms between them
(`MAX_PAGES`, `PAGE_DELAY_MS` on `RealEstateWorker`). Portals are scanned in
parallel with each other, never within one portal.

## Architecture

```
Console.py          the cli (plac); prints statistics and the archive report
ImmoScanner.py      orchestrates a scan: locates, fans out, de-duplicates
Countries/          which portals serve a country, and geonames lookups
Workers/            one class per portal, on a shared fetch-and-walk base
Means/              what is searched for (Research) and what comes back (Result)
Intellectuals/      statistics over a set of results
Archives/           sqlite archive of every listing ever seen
```

A scan runs as follows.

1. `CountryFactory` builds the country, which owns the list of workers.
2. Whichever of city and postal code is missing is filled in from geonames.
3. Each worker is handed its own `RealEstateResearch` and runs in its own
   thread.
4. `RealEstateWorker.get_findings` walks the result pages and turns each card
   into a `RealEstateResearchResult`.
5. The per-portal lists are flattened and de-duplicated into one set.
6. Statistics are computed, the archive is compared, the report is printed.

### Writing a worker

`RealEstateWorker.get_findings` is the whole page walk; a portal class fills in
the parts that differ:

| hook | role |
| --- | --- |
| `url_builder(research, page)` | the search url for one page |
| `CARD_SELECTOR` | the result cards on that page |
| `extract_findings(card)` | one card to one result |
| `total_results(soup)` | how many listings the portal claims, when it says |
| `PROBE_SELECTOR` | proof that a plain GET returned the real list |
| `WAIT_FOR` | what to await before reading the dom, on the browser path |
| `fetch_page(research, page)` | override only when the list is not in the markup |

Register the class in the country under `Countries/`, and capture a search page
into `tests/fixtures/` so its extractors are covered offline.

## Technical choices

**rustwright instead of playwright.** [rustwright](https://github.com/Skyvern-AI/rustwright)
is a Rust rewrite of Playwright with a drop-in `sync_api`, so the switch was one
import. It drives Chromium over raw CDP with no Node driver subprocess in the
path, and it reuses whatever Chromium is already installed instead of demanding
its own pinned download.

**Plain HTTP first, browser second.** immoweb and immovlan server-render their
result lists, and a `requests` GET reads one in well under a second where a
browser needs several. Each worker tries HTTP, checks `PROBE_SELECTOR` to see
whether the real list came back, and switches to the browser permanently on the
first miss — so a portal that needs a browser pays for exactly one wasted GET.
comparis is such a portal: it refuses plain HTTP whatever the headers say,
because the rejection is on the TLS fingerprint, not on the request.

**Structured payloads over css selectors.** Both Belgian and Swiss portals ship
their listings as JSON inside the page, and that JSON holds fields the rendered
markup does not: surfaces, bedroom counts, coordinates. immoweb puts the whole
listing on its card's Vue component, comparis serves `__NEXT_DATA__`. Class
names churn with every redesign; these payloads are the portal's own data model
and move far less. immoweb's attribute disappears when Vue hydrates the page, so
the browser path keeps a markup reader as a fallback.

**Walking pages, not counting them.** immoweb renders its pagination and its
result total client-side, so a plain GET never sees either. The walk stops on
the first empty page, or earlier when the portal announces a total it has
already collected — counting distinct ids, since immoweb repeats a sponsored
card on every page. A page past the last one stops the walk instead of
discarding everything collected so far.

**A portal-neutral vocabulary.** A search is expressed as `buy`/`rent` and
`any`/`house`/`apartment`; each worker maps those onto its own url scheme
(`a-vendre`, `acheter`, `DealType: 20`). Callers never have to know that
immoweb spells "all types" `maison-et-appartement`.

**Two de-duplication keys.** The same flat is listed on several portals under
different ids. Listings are matched on `(postal code, price, surface, bedrooms)`,
which every portal supplies, *and* on `(latitude, longitude, price)` rounded to
about eleven metres for the portals that geocode. Either match is enough, so a
pair that disagrees by one square metre still collapses.

**Developments are not properties.** A new-build is advertised as a price range
over a whole building. Averaging that into a median would describe nothing, so
these carry `is_project`, `price_min` and `price_max`, stay out of the
statistics, and are still reported rather than silently dropped.

**Archive rather than snapshot.** A scan on its own cannot tell you what is new,
what was cut, or what sold. `--store` keeps every listing and every price it has
ever shown in sqlite, keyed by portal and id and scoped by search, and each run
reports the difference.

**lxml everywhere.** Several portals, geonames included, serve unclosed tags
that `html.parser` cannot recover from — it swallowed a whole geonames table
into its first row, which is how postal code lookups used to return a
neighbouring village.

**Anti-bot walls are reported, not worked around.** A captcha interstitial
raises `BotWallError` instead of parsing as an empty result set, so a blocked
portal never passes for a market with nothing for sale.

## Portal status

| Portal | Country | State |
| --- | --- | --- |
| immoweb.be | BE | works — listing JSON embedded in the server-rendered cards |
| immovlan.be | BE | works — moved off `immo.vlan.be`, which now 503s |
| comparis.ch | CH | works — `__NEXT_DATA__` payload; needs the browser |

homegate.ch and immoscout24.ch sit behind DataDome on every entry point, their
APIs included, so they have no worker. Their listings still come through:
comparis aggregates both, and every result names its originating portal in
`source`.

## Tests

```bash
uv run pytest            # offline, against search pages captured in tests/fixtures
uv run pytest -m live    # hits the real portals; run weekly in CI as a canary
```

A portal redesign is silent — a scan just returns less, and the numbers drift.
The offline suite asserts on the exact selectors and payload keys the workers
depend on, so a break is a failure; recapture the fixture when a portal changes
for good. The live suite is the canary, and CI runs it every Monday.
