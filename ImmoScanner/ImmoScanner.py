import itertools
import logging
from concurrent.futures import ThreadPoolExecutor

import tldextract

from .Countries.CountryFactory import CountryFactory
from .Intellectuals.StatisticalInsights import StatisticalInsights
from .Means.RealEstateResearch import ANY, BUY, RENT, RealEstateResearch

logger = logging.getLogger(__name__)

#: portals are independent, and each worker owns its own http session and
#: browser, so they are scanned side by side rather than one after the other
MAX_CONCURRENT_PORTALS = 4


class ImmoScanner:
    def research_real_estate(
        self,
        country_name,
        postal_code="",
        city="",
        type=ANY,
        rent_or_buy=BUY,
    ):
        country = CountryFactory().generate_country_given_name(name=country_name)
        if country is None:
            raise ValueError(f"the country {country_name} is not implemented")

        websites = country.get_real_estate_websites()
        if not websites:
            raise ValueError(f"no real estate website registered for {country_name}")

        if not postal_code:
            postal_code = country.fetch_postal_code_given_city(city)

        if not city:
            city = country.fetch_city_given_postal_code(postal_code)

        logger.info(f"searching {city} ({postal_code}) in {country_name}")

        def scan(website):
            # fill_empty_fields mutates the research, so each portal gets its own
            research = RealEstateResearch(
                postal_code=postal_code,
                city=city,
                type=type,
                rent_or_buy=rent_or_buy,
            )
            try:
                return website.get_findings(research)
            except Exception as error:
                logger.error(f"{website.domain_name}: search failed ({error})")
                return []

        with ThreadPoolExecutor(
            max_workers=min(len(websites), MAX_CONCURRENT_PORTALS)
        ) as pool:
            return list(pool.map(scan, websites))

    def research_real_estate_url(self, country_name, url):
        country = CountryFactory().generate_country_given_name(name=country_name)
        if country is None:
            raise ValueError(f"the country {country_name} is not implemented")

        domain = tldextract.extract(url).registered_domain
        results = []
        for website in country.get_real_estate_websites():
            if domain != website.domain_name:
                continue
            results.append(website.get_findings(RealEstateResearch(url=url)))

        if not results:
            logger.warning(f"no worker registered for {domain}")

        return results

    def research_gross_yield(self, country_name, postal_code="", city="", type=ANY):
        """Scan the same area twice, for sale and to let, and compare the two."""
        selling = self.duplicate_finder(
            self.research_real_estate(
                country_name, postal_code, city, type, rent_or_buy=BUY
            )
        )
        renting = self.duplicate_finder(
            self.research_real_estate(
                country_name, postal_code, city, type, rent_or_buy=RENT
            )
        )
        return self.get_insights(selling, renting)

    def duplicate_finder(self, results):
        """Flatten per-portal results, dropping the same property seen twice.

        Listings are matched on :meth:`RealEstateResearchResult.fingerprint`,
        which identifies the property rather than the advertisement.
        """
        flat_list = [
            item
            for item in itertools.chain(*results)
            if item.is_project or (item.price and item.livable_square_meters)
        ]

        unique_items = []
        seen = set()
        for item in flat_list:
            keys = [item.fingerprint(), item.geo_fingerprint()]
            keys = [key for key in keys if key is not None]
            if any(key in seen for key in keys):
                continue
            seen.update(keys)
            unique_items.append(item)

        return unique_items

    def get_insights(self, selling_results, renting_results=None):
        # A development has a price range over a whole building; averaging it
        # in would describe no property at all.
        properties = [item for item in selling_results if not item.is_project]

        selling = StatisticalInsights(properties)
        insights = {
            "listings": len(properties),
            "projects": len(selling_results) - len(properties),
            "selling_mean_price": selling.calculate_mean_price(),
            "selling_median_price": selling.calculate_median_price(),
            "selling_median_price_per_m2": selling.price_per_square_meter_median(),
        }

        if renting_results:
            rentals = [item for item in renting_results if not item.is_project]
            renting = StatisticalInsights(rentals)
            insights["rental_listings"] = len(rentals)
            insights["renting_mean_price"] = renting.calculate_mean_price()
            insights["renting_median_price"] = renting.calculate_median_price()
            insights["renting_median_price_per_m2"] = (
                renting.price_per_square_meter_median()
            )
            insights["gross_yield_percent"] = StatisticalInsights.gross_yield(
                insights["renting_median_price"], insights["selling_median_price"]
            )

        for name, value in insights.items():
            logger.info(f"{name}: {value}")

        return insights
