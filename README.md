<div align="center">

<img src="docs/logo.svg" alt="ImmoScanner" width="440">

**Scan the real estate portals of a town, a province or a canton. Get price statistics, rental yields and the listings priced under their neighbourhood, and see what changed since your last scan.**

[![Tests](https://github.com/UyttenhoveSimon/ImmoScanner/actions/workflows/tests.yml/badge.svg)](https://github.com/UyttenhoveSimon/ImmoScanner/actions/workflows/tests.yml)
[![Live canary](https://github.com/UyttenhoveSimon/ImmoScanner/actions/workflows/canary.yml/badge.svg)](https://github.com/UyttenhoveSimon/ImmoScanner/actions/workflows/canary.yml)
![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.15-blue?logo=python&logoColor=white)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
<br>
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/badge/types-ty-261230)](https://github.com/astral-sh/ty)
[![prek](https://img.shields.io/badge/hooks-prek-orange)](https://github.com/j178/prek)
[![Countries](https://img.shields.io/badge/countries-🇧🇪_🇨🇭_🇫🇷_🇩🇪-informational)](#-supported-portals)

[Quick start](#-quick-start) •
[Usage](#-usage) •
[Explorer](#-exploring-an-archive) •
[Portals](#-supported-portals) •
[Architecture](#-architecture) •
[Contributing](#-contributing)

</div>

---

<p align="center">
  <img src="docs/cli.svg" alt="immoscanner --help: the scan, yield, brrrr and serve commands" width="760">
</p>

<p align="center">
  <img src="docs/explorer.png" alt="The ImmoScanner explorer comparing towns in Walloon Brabant" width="900">
  <br>
  <em>The explorer, comparing towns side by side. <a href="#try-it-without-scanning">Try it with demo data</a> in two commands.</em>
</p>

## ✨ Features

- 🔎 **Search by city, postal code, region or URL** in Belgium 🇧🇪, Switzerland 🇨🇭, France 🇫🇷 and Germany 🇩🇪 (some French and German portals wall bots off, see [Portals](#-supported-portals))
- 📊 **Price statistics**: mean, median, median per m², typical price range
- 💰 **Gross rental yield**: compares sale prices with rents in the same area
- 🗂️ **History**: save each scan and see what is new, cheaper, more expensive or gone
- 🧹 **No double counting**: a flat listed on three websites counts once
- 🌐 **Web explorer**: compare places, browse listings and see prices on a map, in four languages
- 🎯 **Narrowing**: count only listings with enough bedrooms, rooms, living area or land
- 🔨 **Fixer-uppers**: spot listings that need work, from their description and energy certificate (PEB/EPC)
- 🏗️ **BRRRR ranking**: rank fixer-uppers by how far under their postal code they sell, with rent and equity after works
- 🤝 **Polite**: limits how many pages it reads and pauses between them

## 🚀 Quick start

Install the command once, with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/UyttenhoveSimon/ImmoScanner
immoscanner scan Belgium --city Namur
```

Portals that only answer a real browser are read with Chromium; download it once with `uvx --from git+https://github.com/UyttenhoveSimon/ImmoScanner python -m rustwright install chromium`.

Or work from a clone (every `immoscanner` command below then runs as `uv run immoscanner`):

```bash
git clone https://github.com/UyttenhoveSimon/ImmoScanner && cd ImmoScanner
uv sync
uv run python -m rustwright install chromium
uv run immoscanner scan Belgium --city Namur
```

> [!TIP]
> To use a specific Chromium build, set the `IMMOSCANNER_BROWSER_PATH` environment variable.

### Try it without scanning

Build a demo archive of made-up listings (seven towns, four weekly scans), then open it in your browser:

```bash
uv run python scripts/demo_archive.py
uv run immoscanner serve demo.db
```

Then go to **http://127.0.0.1:8765**.

## 📖 Usage

Pick a **command**, give the **country**, then say where to look: a city, a postal code, a region, or a search URL copied from a portal.

```bash
uv run immoscanner scan Belgium --city Namur
uv run immoscanner scan Belgium --region "Brabant wallon" --max-pages 60
uv run immoscanner scan Belgium --postal-code 1000 --type apartment --rent
uv run immoscanner scan Switzerland --postal-code 1618 --output ch.json
uv run immoscanner scan Belgium --city Namur --store namur.db
uv run immoscanner scan Belgium --url "https://www.immoweb.be/fr/recherche/maison/a-vendre/namur/5000?countries=BE"
uv run immoscanner yield Belgium --postal-code 1000 --type apartment
uv run immoscanner brrrr Belgium --postal-code 4000,4020 --works-per-m2 900
uv run immoscanner serve namur.db
```

Every command explains itself with `--help`, for instance `uv run immoscanner brrrr --help`.

### Commands

| Command | What it does |
| --- | --- |
| `scan COUNTRY` | Read every portal for a place, print price statistics, and what changed since the last scan |
| `yield COUNTRY` | Scan for sale and to let, and work out the gross rental yield |
| `brrrr COUNTRY` | Scan for sale and to let, and rank fixer-uppers against their postal code |
| `serve ARCHIVE.db` | Open saved scans in your browser |

### Options

| Option | Commands | What it does |
| --- | --- | --- |
| **Where to look** | | |
| `-p`, `--postal-code CODE` / `-c`, `--city NAME` | scan, yield, brrrr | Give either one; the other is looked up for you. Several postal codes can be given comma separated |
| `-g`, `--region NAME` | scan, yield, brrrr | Search a whole province or canton instead of one town |
| `-u`, `--url URL` | scan | Scan a search page copied from a portal, following its pages |
| **What to look for** | | |
| `-t`, `--type any\|house\|apartment` | scan, yield, brrrr | Type of property |
| `-r`, `--rent` | scan | Look at rentals instead of properties for sale |
| `--source NAMES` | scan, yield, brrrr | Only keep listings that came from these websites (comma separated) |
| `--exclude-source NAMES` | scan, yield, brrrr | Leave out listings that came from these websites (comma separated) |
| `-m`, `--max-pages N` | scan, yield, brrrr | How many result pages to read per portal (default: the portal's own, `20`) |
| `-k`, `--condition any\|works\|renovate` | scan, brrrr | Only keep listings that need at least this much work |
| **Investing** | | |
| `-e`, `--works-per-m2 EUR` | brrrr | Renovation budget per m², taken off the equity and added to the cost (default `0`) |
| **Output** | | |
| `-l`, `--top N` | scan, brrrr | How many listings to print (default `15`) |
| `-s`, `--store FILE.db` | scan, brrrr | Save the scan, and show what changed since the previous one |
| `-o`, `--output FILE.json` | scan, brrrr | Save the listings to a JSON file |
| `-n`, `--port N` | serve | Port for the browser view (default `8765`) |
| `--debug` | all, before the command | Log every listing as it is read: `immoscanner --debug scan ...` |

### What a scan shows

```console
$ uv run immoscanner scan Belgium --postal-code 5000 --type house --store namur.db
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

How to read it:

- **`159 listings, 117 unique`**: the portals returned 159 listings, and 117 were left once duplicates were removed.
- **`listings` / `projects`**: those 117 are split into ordinary properties (111) and new-build developments (6). Only ordinary properties count towards the statistics.

**Scan again later** with the same `--store` file, and you only see what changed:

```console
since the last run: 0 new, 2 repriced, 1 gone, 114 unchanged
  down    395,000 -> 379,000 € https://www.immoweb.be/fr/annonce/...
  gone    289000.0 Namur https://immovlan.be/fr/detail/...
```

**With `yield`**, the area is scanned twice, once for sale and once for rent:

```console
$ uv run immoscanner yield Switzerland --postal-code 1003 --type apartment
median_price_per_m2: 11,033
rental_median_price: 2,500
rental_median_price_per_m2: 33.36
gross_yield_percent: 2.04
```

### Finding fixer-uppers

No portal gives a building's condition on its search pages, so ImmoScanner reads it from what they do give:

- **the description**: "à rénover", "gros travaux", "idéal investisseur", "te renoveren"… mean a renovation; "à rafraîchir", "quelques travaux", "op te frissen"… mean some works. "Aucuns travaux à prévoir" is read as the opposite of what it contains.
- **the energy certificate**: F or G means a renovation, E means works.

Every listing keeps the phrases that decided its condition, so a false positive shows at a glance. When the same house is on two portals, the copy kept learns what the other one knew (immoweb only shows a title, immovlan the whole description).

The figures in the two examples below are illustrative.

```console
$ uv run immoscanner scan Belgium --postal-code 4000 --type house --condition renovate
listings: 212
...
38 of 212 need renovate
    89,000 EUR  120 m²    742/m² PEB G 4000 Liège [« a renover », PEB G]
    https://www.immoweb.be/fr/annonce/...
```

The statistics and the archive still cover every listing; `--condition` only narrows what is printed and written to `--output`.

### BRRRR: ranking fixer-uppers

Buy, Rehab, Rent, Refinance, Repeat works when a property bought under its neighbourhood's price, once brought up to its standard, is worth enough to refinance what went into it. The `brrrr` command scans the area for sale and to let, then measures every listing that needs work against its own postal code:

- **reference price per m²**: the median of the listings in the same postal code that show no sign of needing work, the nearest thing a search page has to an after-repair value. With fewer than five of those, every listing of the postal code stands in, then the whole scan; the line says so.
- **discount**: how far under that reference the asking price per m² is. Listings are ranked on it.
- **after works / equity**: the reference times the surface, minus the price and `--works-per-m2`.
- **rent and gross yield**: the median rent per m² to let in the postal code, over price plus works.

```console
$ uv run immoscanner brrrr Belgium --postal-code 4000,4020,4030,4100 --type house --works-per-m2 900
by postal code: median price/m², rent/m², gross yield, needing work
  4000 Liège               2,150/m²  10.80/m²   6.0%  61/212
  4100 Seraing             1,480/m²   9.10/m²   7.4%  44/97
  ...
71 listings needing works, best discount to their postal code first:
    +48% vs 2,150/m²     139,000 EUR  125 m²  1,112/m² PEB F 4000 Liège [« a renover », PEB F]
    after works ~268,750, equity 17,250, rent ~1,350/month, 6.4% gross on all-in cost
    https://www.immoweb.be/fr/annonce/...
```

`--condition renovate` keeps only the heavy renovations; by default `brrrr` takes everything that needs some work. These are asking prices and a flat works budget: a first sort through a few hundred listings, not a valuation.

### Filtering by original website

Some portals, like comparis, collect listings from other websites. Each listing then says where it originally came from, in its `source` field. `--source` and `--exclude-source` filter on that field. The match ignores case and accepts part of a name, so `homegate` matches `homegate.ch`. A portal that publishes its own listings counts as their source.

Filtering happens **before** duplicates are removed. So if a flat appears on several websites and you ask for one of them, you get that website's copy.

```console
$ uv run immoscanner scan Switzerland --postal-code 1003 --type apartment --rent --source homegate
102 listings, 13 from the asked sources, 11 unique
```

### JSON output

`--output` writes one JSON object per listing, with duplicates already removed.

<details>
<summary>Example listing</summary>

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

</details>

> [!NOTE]
> For a new-build development, `price` is `0` and the price range is in `price_min` and `price_max`.
> `latitude` and `longitude` are only filled in when the portal publishes a location.

## 🗺️ Exploring an archive

Scan a few places into the same file, then open it in your browser:

```bash
uv run immoscanner scan Belgium --postal-code 1410 --store be.db
uv run immoscanner scan Belgium --postal-code 1420 --store be.db
uv run immoscanner scan Belgium --postal-code 1400 --store be.db
uv run immoscanner serve be.db
```

Then go to **http://127.0.0.1:8765**. From there you can:

- 📈 **Compare places** on the *Places* page: listings for sale and to let, median price, price per m², median rent and yield, one row per town.
- 🧭 **Jump to any place** from the sidebar, or type part of its name or postal code to find it.
- 🏠 **Open a place** to see its key figures (median, price per m², typical price range, yield), switch between *For sale* and *To let*, and browse its listings. Listings are marked **new** or **gone** compared with the previous scan, and you can filter them by words or website.
- 📉 **See price changes**: the *Price changes* tab lists every listing whose price moved since the first scan.
- 🔍 **Click a listing** to see its details, a chart of its price over time, and a link to the original ad.
- 💰 **Compare rental yields** on the *Rental yield* page, for every place scanned both for sale and to let.
- 🗺️ **See prices on a map** on the *Map* page: one circle per locality, coloured by median price per m² and sized by the number of listings, for sale or to let. A region scan is split into its towns. Hover a circle for its figures; click it to open the place.
- 🎯 **Narrow everything down** from the sidebar: at least so many bedrooms or rooms, a minimum living area or plot of land. Every page then counts only the listings that match, including the medians, the yields and the map. A listing that doesn't give the figure is left out. Land area comes from immoweb only, since immovlan and comparis don't publish it in their search results.
- ↕️ **Sort any table** by clicking a column heading. Click again to reverse the order.
- 🔖 **Bookmark any view**: each place has its own address, and the browser's back button works.
- 🌍 **Pick your language**: English, French, Dutch or German, from the menu at the top.
- ➕ **Add a place** with the *+ Scan a place* button. The scan runs in the background and the page opens the place when it is done. Only one scan runs at a time: if one is already running, a new request is turned down, not queued.

## 🐍 As a library

```python
from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Means.RealEstateResearch import APARTMENT, RENT

scanner = ImmoScanner()
results = scanner.research_real_estate(
    "Belgium", postal_code="1000", type=APARTMENT, rent_or_buy=RENT
)
listings = scanner.duplicate_finder(results)
insights = scanner.get_insights(listings)
```

## 🛡️ Being polite to the websites

By default a scan reads at most **20 pages per portal** and waits **800 ms** between pages. These limits are `MAX_PAGES` and `PAGE_DELAY_MS` on `RealEstateWorker`. Different portals are scanned at the same time, but the pages of one portal are read one after another.

## 🏗️ Architecture

```
Console.py          the command line: scan, yield, brrrr and serve subcommands
ImmoScanner.py      runs a scan: finds the place, asks each portal, removes duplicates
Countries/          which portals cover each country, and postal code lookups
Workers/            one class per portal, sharing a common base
Means/              what is searched for (Research) and what comes back (Result)
Intellectuals/      statistics, condition reading, BRRRR ranking
Archives/           the SQLite archive of every listing ever seen
Showrooms/          the browser view of an archive, and the scans it starts
```

**What happens during a scan:**

1. `CountryFactory` creates the country, which knows which portals to use.
2. If you gave only a city or only a postal code, the other is looked up on geonames.
3. Each portal gets its own `RealEstateResearch` and runs in its own thread.
4. `RealEstateWorker.get_findings` reads the result pages and turns each listing into a `RealEstateResearchResult`.
5. The listings from all portals are combined, and duplicates are removed.
6. Statistics are computed, compared with the archive, and printed.

### Adding a portal

`RealEstateWorker.get_findings` already handles reading the pages. A new portal only fills in what is specific to it:

| Hook | What it is for |
| --- | --- |
| `url_builder(research, page)` | The search URL for a given page |
| `CARD_SELECTOR` | How to find the listings on a page |
| `extract_findings(card)` | How to turn one listing into a result |
| `total_results(soup)` | How many listings the portal says it has, if it says |
| `PROBE_SELECTOR` | Something that proves a simple download returned the real listings |
| `WAIT_FOR` | What to wait for before reading the page, when a browser is used |
| `fetch_page(research, page)` | Only override this if the listings are not in the page's HTML |
| `SEARCH_BY_PLACE`, `SEARCH_BY_REGION` | What it can search by itself; otherwise it follows a copied `--url` |
| `VERIFIED` | `False` until its reader has been checked on a captured page |

Then add the class to its country under `Countries/`, and save a search page into `tests/fixtures/` so it can be tested without going online.

## 🧠 Design choices

Click a topic to expand it.

<details>
<summary><b>Why rustwright instead of Playwright</b></summary>

[rustwright](https://github.com/Skyvern-AI/rustwright) is a Rust rewrite of Playwright with the same Python API, so switching took one import change. It controls Chromium directly, without the separate Node.js process Playwright needs, and it uses the Chromium you already have instead of downloading its own.

</details>

<details>
<summary><b>Cheapest download method first</b></summary>

Each page is downloaded in the cheapest way that works:

1. a plain HTTP request with `requests`;
2. the same request through [curl_cffi](https://github.com/lexiforest/curl_cffi), which looks like a real browser at the network level;
3. a real browser.

immoweb and immovlan work with a plain request, which takes well under a second per page, against several seconds with a browser. comparis rejects plain requests based on how the connection is made, whatever the headers say. So it uses curl_cffi, which brought a scan down from 15 s to 6 s.

If a method fails, it is not tried again for the rest of the scan, so a portal that needs a browser only wastes one attempt per method. Once a method has worked, it is kept: portals return a 404 error for a page past the last one, and that must not be mistaken for the method failing.

</details>

<details>
<summary><b>Reading the portal's own data, not the page layout</b></summary>

Both the Belgian and the Swiss portals include their listings as JSON inside the page. That JSON has more detail than what is displayed: surface, number of bedrooms, location. immoweb attaches it to each listing on the page, and comparis to a `__NEXT_DATA__` block.

Page layouts change with every redesign, but this data changes much less often. On immoweb the data disappears once the page has fully loaded in a browser, so when a browser is used, the scanner falls back to reading the page layout.

</details>

<details>
<summary><b>Knowing when to stop reading pages</b></summary>

immoweb only shows the number of pages and results after the page has loaded in a browser, so a plain download can't see them. The scanner simply keeps going until it reaches an empty page, or until it has as many listings as the portal says it has.

It counts each listing only once, because immoweb repeats the same sponsored listing on every page. Reaching a page past the last one ends the scan normally and keeps everything collected so far.

</details>

<details>
<summary><b>Writing town names the way each portal expects</b></summary>

The two Belgian portals want opposite things, and getting it wrong silently loses listings.

- **immoweb** uses only the postal code and ignores the town name. But an apostrophe in the name breaks the search: "Braine-L'Alleud" returned **no listings at all**, while the postal code alone returns 288. So immoweb is searched with `1420` only.
- **immovlan** needs both. With only a postal code, it picks the first town under that code: `1400` gives Monstreux with 2 listings, not Nivelles with about a hundred. So it gets `1400-nivelles`. If immovlan doesn't recognise the name, it searches the whole country instead. The scanner now warns about that, instead of reporting a town with 32 000 properties.

</details>

<details>
<summary><b>Each portal searches regions its own way</b></summary>

Each of the three portals can search a whole province or canton directly, instead of going through every postal code in it. They just write it differently:

| Portal | How a region is written |
| --- | --- |
| immoweb | in the URL path: `/brabant-wallon/province` |
| immovlan | as a URL parameter: `?provinces=brabant-wallon` |
| comparis | in the location field: `Canton Vaud` (just `Vaud` would mean the *town*) |

Regions are listed in French, and each portal translates them as needed. That's where the exceptions are handled: for example, comparis understands "Schwyz" but not "Schwytz". All 11 Belgian provinces and all 26 Swiss cantons were tested on the real websites.

</details>

<details>
<summary><b>A page limit, with a clear warning</b></summary>

A scan reads at most `--max-pages` pages per portal, 20 by default. That's about 600 listings on immoweb and 400 on immovlan. A town never reaches that limit, but a province always does: Brabant wallon alone has 3 000 listings.

When the limit is reached, you only get the first pages in the order the portal chose, which is not a fair sample of the market. The scanner tells you so clearly, so you don't mistake the statistics for the full picture.

</details>

<details>
<summary><b>One vocabulary for all portals</b></summary>

You always search with `buy`/`rent` and `any`/`house`/`apartment`, and each portal translates that into its own terms (`a-vendre`, `acheter`, `DealType: 20`). You never need to know that immoweb calls "all types" `maison-et-appartement`.

</details>

<details>
<summary><b>Two ways to compute the yield</b></summary>

The usual way divides the median rent by the median price. The catch: rentals tend to be small and properties for sale tend to be large, so this ends up comparing the rent of a studio with the price of a family house.

The other way divides the median **per square metre** values, which removes the size difference.

Both are shown, because they don't always agree. On four towns in Walloon Brabant, they pick a different winner: per square metre, Nivelles leads with 5.79%; on plain medians, Wavre leads with 4.13%. The explorer shows both side by side, highlights the best place for each, and shows the medians they come from.

</details>

<details>
<summary><b>How duplicates are found</b></summary>

The same flat is often listed on several websites, with a different ID on each. Two listings are treated as the same property when they match on either:

- **postal code, price, surface and bedrooms**, which every portal provides; **or**
- **location and price**, with the location rounded to about 11 metres, for portals that publish a location.

Matching on either one is enough, so two listings whose surface differs by one square metre are still recognised as one.

immoweb and comparis publish locations; immovlan doesn't. immoweb also hides it on sponsored listings and when the seller hides the address, so about half of a Belgian scan has no location. Those listings rely on the first rule, which is why it only uses information every portal provides.

The location rule helps most on comparis, where the same property often arrives from several websites. Its one weakness: two identical flats in the same building, at the same price and size, look like one listing posted twice, and are merged. Real duplicates are far more common, so this is a deliberate trade-off, and a test documents it.

</details>

<details>
<summary><b>New-build developments are kept apart</b></summary>

A new-build project is advertised as a price range for a whole building. Mixing that into a median wouldn't mean anything. So these listings are marked with `is_project`, carry `price_min` and `price_max`, are left out of the statistics, and are still shown in the results.

</details>

<details>
<summary><b>Keeping a history, not just a snapshot</b></summary>

A single scan can't tell you what is new, what got cheaper, or what sold. With `--store`, every listing and every price it has ever had is saved in a SQLite file, and each scan shows what changed since the last one.

</details>

<details>
<summary><b>An explorer with no extra dependencies</b></summary>

The archive is a SQLite file and the explorer is only meant for you, on your own computer. So it is built with Python's built-in web server, a single HTML page and hand-drawn SVG charts, with no web framework or charting library.

The map is the one exception: it uses [Leaflet](https://leafletjs.com) and OpenStreetMap tiles, loaded from the internet only when the *Map* page is opened. The rest of the explorer still works offline.

Medians are calculated in Python, because SQLite has no median function and an archive has thousands of rows, not millions.

To dig deeper into the data, use pandas or DuckDB. Both can read the archive file directly, without being added to the scanner.

</details>

<details>
<summary><b>Using lxml to read HTML</b></summary>

Several websites, including geonames, have HTML that Python's built-in parser can't handle: it once squeezed a whole table into its first row. That's why postal code lookups used to return a neighbouring village.

</details>

<details>
<summary><b>Anti-bot pages are reported, not bypassed</b></summary>

If a portal shows a captcha, the scanner raises a `BotWallError` instead of returning zero listings. That way, a blocked portal is never mistaken for a market with nothing for sale.

</details>

## 🌍 Supported portals

| Portal | Country | Where the data is read | Downloaded with | Location |
| --- | :---: | --- | --- | :---: |
| immoweb.be | 🇧🇪 | JSON inside each listing | plain HTTP | partly |
| immovlan.be | 🇧🇪 | schema.org tags on each listing | plain HTTP | ❌ |
| comparis.ch | 🇨🇭 | the `__NEXT_DATA__` block | curl_cffi | ✅ |
| bienici.com | 🇫🇷 | its JSON api (`realEstateAds.json`) | plain HTTP | blurred |
| leboncoin.fr ⛔ | 🇫🇷 | the `__NEXT_DATA__` block | DataDome wall | ✅ |
| seloger.com ⛔ | 🇫🇷 | the result cards (AVIV layout), from a copied search url | DataDome wall | ❌ |
| pap.fr ⛔ | 🇫🇷 | schema.org JSON-LD, from a copied search url | Cloudflare challenge | if published |
| kleinanzeigen.de | 🇩🇪 | the result cards, read by their text | plain HTTP | ❌ |
| immobilienscout24.de ⛔ | 🇩🇪 | schema.org JSON-LD, from a copied search url | its own wall | if published |
| immowelt.de | 🇩🇪 | the result cards (AVIV layout) | plain HTTP | ❌ |

The French and German readers were written before any page of those portals could be reached from where they were written. A capture run on GitHub then told them apart:

- ✅ **bienici.com**, **kleinanzeigen.de** and **immowelt.de** work: their readers, and the way they turn a place into a search url, are checked on captured pages (`tests/fixtures/bienici_search.json`, `kleinanzeigen_search.html`, `immowelt_search.html`).
- ⛔ **leboncoin.fr**, **seloger.com**, **pap.fr** and **immobilienscout24.de** answered with an anti-bot wall even from a real browser. Their readers are kept, unverified, in case they answer from elsewhere (a home connection, say); the scan reports the wall as a `BotWallError` rather than an empty market.

A scan logs a warning for every unverified portal it uses. To check them again:

- the **portal capture** workflow (GitHub Actions, run on demand or whenever a reader changes) saves one result page per portal and what the reader made of it on the `portal-captures` branch; locally: `uv run python scripts/capture_portals.py captures/`;
- the **live tests** list the unverified ones as expected failures, and report `XPASS` the day one starts working: `uv run pytest -m live`.

seloger.com, pap.fr and immobilienscout24.de key their searches by ids of their own, so they follow a search url copied from the site: `immoscanner scan France --url "https://www.seloger.com/..."`. A place search in France uses bienici.com and leboncoin.fr; in Germany, kleinanzeigen.de and immowelt.de. A région search in France uses bienici.com only.

- immovlan moved away from `immo.vlan.be`, which now returns a 503 error.
- **homegate.ch** and **immoscout24.ch** block automated access everywhere, including their APIs, so they aren't scanned directly. Their listings still show up through comparis, which collects both, and each listing names its original website in `source`.

## 🧪 Tests

The project is managed with [uv](https://docs.astral.sh/uv/). [Ruff](https://docs.astral.sh/ruff/) formats the code and lints it with every rule it has, minus the few listed, with their reasons, in `pyproject.toml`. [ty](https://docs.astral.sh/ty/) type-checks the whole tree; type annotations are required in `Means/`, `Intellectuals/`, `ImmoScanner.py` and `Console.py`; `Archives/`, `Countries/`, `Showrooms/` and `Workers/` follow folder by folder. The hooks (Ruff, ty, the lockfile check, whitespace) run with [prek](https://github.com/j178/prek). `uv sync` installs all of it:

```bash
uv sync
uv run prek install               # run the hooks on every commit
uv run prek run --all-files       # what CI checks
uv run ruff check --fix .         # lint on its own
uv run ruff format .              # format on its own
uv run ty check                   # type-check on its own
```

```bash
uv run pytest                     # offline, using saved copies of portal pages
uv run pytest --cov               # with coverage: 99% today, CI requires at least 95%
uv run pytest -m live             # against the real websites
```

When a portal redesigns its website, nothing crashes: scans just quietly return fewer listings and the numbers drift. Two kinds of tests guard against that:

- **Offline tests** run on saved copies of each portal's pages, in `tests/fixtures/`. They check the exact page elements and data fields the scanner relies on, so a change shows up as a failing test. When a portal changes for good, save a fresh copy of its page.
- **Live tests** run against the real websites, every Monday in CI, as an early warning.

Apart from the live tests, nothing goes online: geonames, the portals, the HTTP clients and the browser are all replaced by saved pages or fakes.

<details>
<summary>Test files and what they cover</summary>

| File | Covers |
| --- | --- |
| `test_workers.py` | Reading listings from saved search pages |
| `test_fallbacks.py` | What each portal does when data is missing, and the shared defaults |
| `test_fetching.py` | The download methods and page reading, fully simulated |
| `test_worker.py` | HTTP and browser sessions, and closing them |
| `test_geolocation.py` | Reading locations, and which listings they merge |
| `test_countries.py` | Postal code lookups, and which portals each country uses |
| `test_pipeline.py` | A full scan: all portals, failures, search URLs |
| `test_scanner.py` | Duplicates, statistics, filtering by website |
| `test_store.py` | The archive and what changed between scans |
| `test_console.py` | The command line: options, printing, saving |
| `test_regions.py` | Provinces and cantons, and how each portal writes them |
| `test_showroom.py` | The explorer's pages and its web server |
| `test_runner.py` | Scans started from the explorer |
| `test_live_portals.py` | The live tests (`-m live`) |

</details>

## 🤝 Contributing

Portals change their pages without notice, so fixes against a fresh capture are always welcome. [CONTRIBUTING.md](CONTRIBUTING.md) says how to set up, check and test a change; [AGENTS.md](AGENTS.md) holds the code map and the pitfalls already met, for coding agents and people alike. Please read the [code of conduct](CODE_OF_CONDUCT.md), and report security issues [privately](SECURITY.md). Changes are listed in the [changelog](CHANGELOG.md).

## 📄 License

[Apache 2.0](LICENSE). If you redistribute ImmoScanner, keep the [NOTICE](NOTICE) file with it.
