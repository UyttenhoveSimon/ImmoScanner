from __future__ import annotations

import itertools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import tldextract

from .Countries.CountryFactory import CountryFactory
from .Intellectuals import Renovation
from .Intellectuals.StatisticalInsights import StatisticalInsights
from .Means.RealEstateResearch import ANY, BUY, RENT, RealEstateResearch

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from .Countries.Country import Country
    from .Means.RealEstateResearchResult import RealEstateResearchResult
    from .Workers.RealEstateWorker import RealEstateWorker

    Listings = list[RealEstateResearchResult]
    #: one list of listings per portal, as the portals returned them
    Groups = list[Listings]

logger = logging.getLogger(__name__)

#: portals are independent, and each worker owns its own http session and
#: browser, so they are scanned side by side rather than one after the other
MAX_CONCURRENT_PORTALS = 4


class ImmoScanner:
    def research_real_estate(
        self,
        country_name: str,
        postal_code: str = "",
        city: str = "",
        region: str = "",
        type: str = ANY,
        rent_or_buy: str = BUY,
        max_pages: int | None = None,
    ) -> Groups:
        codes = [code.strip() for code in str(postal_code).split(",") if code.strip()]
        if len(codes) > 1 and not region:
            return self.research_several_postal_codes(
                country_name,
                codes,
                type=type,
                rent_or_buy=rent_or_buy,
                max_pages=max_pages,
            )

        country = CountryFactory().generate_country_given_name(name=country_name)
        if country is None:
            raise ValueError(f"the country {country_name} is not implemented")

        websites = self.searchable_websites(country, country_name, region)

        region, postal_code, city = self.locate(
            country, country_name, postal_code, city, region
        )

        def scan(website: RealEstateWorker) -> Listings:
            if max_pages:
                website.MAX_PAGES = max_pages
            if not website.VERIFIED:
                logger.warning(
                    f"{website.domain_name}: this reader has not been checked "
                    "against the live site yet; trust its numbers once a live "
                    "test has passed"
                )

            # fill_empty_fields mutates the research, so each portal gets its own
            research = RealEstateResearch(
                postal_code=postal_code,
                city=city,
                region=region,
                type=type,
                rent_or_buy=rent_or_buy,
            )
            try:
                return website.get_findings(research)
            # One portal down must not sink the others, and its traceback
            # would drown the log of a scan that otherwise went fine.
            except Exception as error:  # noqa: BLE001
                logger.error(f"{website.domain_name}: search failed ({error})")  # noqa: TRY400
                return []

        with ThreadPoolExecutor(
            max_workers=min(len(websites), MAX_CONCURRENT_PORTALS)
        ) as pool:
            return list(pool.map(scan, websites))

    @staticmethod
    def searchable_websites(
        country: Country, country_name: str, region: str
    ) -> list[RealEstateWorker]:
        """The country's portals able to run this search without a copied url."""
        websites = country.get_real_estate_websites()
        if not websites:
            raise ValueError(f"no real estate website registered for {country_name}")

        what = "a region" if region else "a place"
        able = [website for website in websites if website.can_search(region)]
        for website in websites:
            if website not in able:
                logger.info(
                    f"{website.domain_name}: cannot search {what} by itself; "
                    "copy a search url from the portal and use scan --url"
                )
        if not able:
            msg = f"no {country_name} portal can search {what}; use scan --url"
            raise ValueError(msg)
        return able

    def research_several_postal_codes(
        self,
        country_name: str,
        codes: Iterable[str],
        type: str = ANY,
        rent_or_buy: str = BUY,
        max_pages: int | None = None,
    ) -> Groups:
        """Search a city and its suburbs: one search each, laid end to end."""
        results: Groups = []
        for code in codes:
            results.extend(
                self.research_real_estate(
                    country_name,
                    postal_code=code,
                    type=type,
                    rent_or_buy=rent_or_buy,
                    max_pages=max_pages,
                )
            )
        return results

    @staticmethod
    def locate(
        country: Country, country_name: str, postal_code: str, city: str, region: str
    ) -> tuple[str, str, str]:
        """Settle what to search: a whole region, or one postal code and city."""
        if region:
            # A whole province or canton: there is no locality to look up.
            matched = country.find_region(region)
            if matched is None:
                raise ValueError(
                    f"{country_name} has no region called {region!r}; "
                    f"try one of {', '.join(country.REGIONS)}"
                )
            logger.info(f"searching {matched} in {country_name}")
            return matched, "", ""

        if not postal_code:
            postal_code = country.fetch_postal_code_given_city(city)
        if not city:
            city = country.fetch_city_given_postal_code(postal_code)
        logger.info(f"searching {city} ({postal_code}) in {country_name}")
        return region, postal_code, city

    def research_real_estate_url(self, country_name: str, url: str) -> Groups:
        country = CountryFactory().generate_country_given_name(name=country_name)
        if country is None:
            raise ValueError(f"the country {country_name} is not implemented")

        # Built from the parts rather than read off `registered_domain`, which
        # tldextract has deprecated.
        extracted = tldextract.extract(url)
        domain = f"{extracted.domain}.{extracted.suffix}".strip(".")
        results: Groups = []
        for website in country.get_real_estate_websites():
            if domain != website.domain_name:
                continue
            if not website.VERIFIED:
                logger.warning(
                    f"{website.domain_name}: this reader has not been checked "
                    "against the live site yet; trust its numbers once a live "
                    "test has passed"
                )
            results.append(website.get_findings(RealEstateResearch(url=url)))

        if not results:
            logger.warning(f"no worker registered for {domain}")

        return results

    def research_gross_yield(
        self,
        country_name: str,
        postal_code: str = "",
        city: str = "",
        region: str = "",
        type: str = ANY,
        max_pages: int | None = None,
    ) -> dict[str, float]:
        """Scan the same area twice, for sale and to let, and compare the two."""
        selling, renting = self.research_both_sides(
            country_name,
            postal_code=postal_code,
            city=city,
            region=region,
            type=type,
            max_pages=max_pages,
        )
        return self.get_insights(selling, renting)

    def research_both_sides(
        self,
        country_name: str,
        postal_code: str = "",
        city: str = "",
        region: str = "",
        type: str = ANY,
        max_pages: int | None = None,
    ) -> tuple[Listings, Listings]:
        """The de-duplicated listings for sale, then those to let, of one area."""
        selling, renting = (
            self.duplicate_finder(
                self.research_real_estate(
                    country_name,
                    postal_code=postal_code,
                    city=city,
                    region=region,
                    type=type,
                    rent_or_buy=deal,
                    max_pages=max_pages,
                )
            )
            for deal in (BUY, RENT)
        )
        return selling, renting

    def filter_by_source(
        self, results: Groups, keep: Iterable[str] = (), drop: Iterable[str] = ()
    ) -> Groups:
        """Keep or drop listings by the portal they originally came from.

        An aggregator republishes other portals' listings and names the origin
        in ``source``; a portal that publishes its own listings leaves it empty
        and is its own origin. Matching is a case-insensitive substring, so
        "homegate" selects "homegate.ch".

        Applied before de-duplication: filtering afterwards would compare
        against a representative that may well be the copy you asked to drop.
        """
        kept = tuple(pattern.casefold() for pattern in keep if pattern)
        dropped = tuple(pattern.casefold() for pattern in drop if pattern)
        if not kept and not dropped:
            return results

        def wanted(item: RealEstateResearchResult) -> bool:
            origin = (item.source or item.platform).casefold()
            if kept and not any(pattern in origin for pattern in kept):
                return False
            return not any(pattern in origin for pattern in dropped)

        return [[item for item in group if wanted(item)] for group in results]

    def duplicate_finder(
        self, results: Iterable[Iterable[RealEstateResearchResult]]
    ) -> Listings:
        """Flatten per-portal results, dropping the same property seen twice.

        Listings are matched on :meth:`RealEstateResearchResult.fingerprint`,
        which identifies the property rather than the advertisement. Each one
        is also assessed for the work it needs, and the copy kept learns what
        the dropped ones knew of the building's condition.
        """
        flat_list = [
            item
            for item in itertools.chain(*results)
            if item.is_project or (item.price and item.livable_square_meters)
        ]

        unique_items: Listings = []
        seen: dict[tuple, RealEstateResearchResult] = {}
        for item in flat_list:
            Renovation.annotate(item)
            keys = [item.fingerprint(), item.geo_fingerprint()]
            keys = [key for key in keys if key is not None]
            kept = next((seen[key] for key in keys if key in seen), None)
            if kept is not None:
                Renovation.merge(kept, item)
                continue
            for key in keys:
                seen[key] = item
            unique_items.append(item)

        return unique_items

    @staticmethod
    def filter_by_condition(
        findings: Iterable[RealEstateResearchResult], condition: str = ANY
    ) -> Listings:
        """Keep the listings that need at least ``condition`` of work."""
        return [item for item in findings if Renovation.meets(item, condition)]

    def get_insights(
        self,
        selling_results: Sequence[RealEstateResearchResult],
        renting_results: Sequence[RealEstateResearchResult] | None = None,
    ) -> dict[str, float]:
        # A development has a price range over a whole building; averaging it
        # in would describe no property at all.
        properties = [item for item in selling_results if not item.is_project]

        # Neutral names: the same call summarises a sale search and a rental
        # one. Only the yield comparison below has a selling and a renting side.
        scanned = StatisticalInsights(properties)
        insights: dict[str, float] = {
            "listings": len(properties),
            "projects": len(selling_results) - len(properties),
            "mean_price": scanned.calculate_mean_price(),
            "median_price": scanned.calculate_median_price(),
            "median_price_per_m2": scanned.price_per_square_meter_median(),
        }

        if renting_results:
            rentals = [item for item in renting_results if not item.is_project]
            renting = StatisticalInsights(rentals)
            insights["rental_listings"] = len(rentals)
            insights["rental_mean_price"] = renting.calculate_mean_price()
            insights["rental_median_price"] = renting.calculate_median_price()
            insights["rental_median_price_per_m2"] = (
                renting.price_per_square_meter_median()
            )
            insights["gross_yield_percent"] = StatisticalInsights.gross_yield(
                insights["rental_median_price"], insights["median_price"]
            )

        for name, value in insights.items():
            logger.info(f"{name}: {value}")

        return insights
