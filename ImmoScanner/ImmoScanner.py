import itertools
import logging
import tldextract
from ImmoScanner.Means.Research import Research
from ImmoScanner.Means.RealEstateResearch import RealEstateResearch
from ImmoScanner.Intellectuals.StatisticalInsights import StatisticalInsights
from ImmoScanner.Countries.CountryFactory import CountryFactory


class ImmoScanner:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)

    def research_real_estate(self, country_name, postal_code="", city=""):
        """Enter arguments in that order 1)Country 2)Type (real estate...) 3)Postal code 4)Buy/Rent   """

        country = CountryFactory().generate_country_given_name(name=country_name)
        websites = country.get_real_estate_websites()

        if websites is None:
            print(f"the country {country} input is not implemented.")

        if not postal_code:
            postal_code = country.fetch_postal_code_given_city(city)

        if not city:
            city = country.fetch_city_given_postal_code(postal_code)

        searches_immo_to_sell = RealEstateResearch(postal_code, city)

        results = list()
        for website in websites:
            results.append(website.get_findings(searches_immo_to_sell))

        return results

    def research_real_estate_url(self, country_name, url):
        research = Research()
        research.url = url

        country = CountryFactory().generate_country_given_name(name=country_name)
        websites = country.get_real_estate_websites()

        if websites is None:
            print(f"the country {country} input is not implemented.")

        results = list()
        parsed_uri = tldextract.extract(research.url)
        for website in websites:
            if parsed_uri.domain == website.domain_name:
                results.append(website.get_findings(research))

        return results

    def duplicate_finder(self, results):
        # results is a list of list with results from each website
        flat_list = list(itertools.chain(*results))

        # all items must have a price and livable square meters
        for item in flat_list:
            if item["price"] is 0:
                flat_list.remove(item)

            if item["livable_square_meters"] is 0:
                flat_list.remove(item)

        unique_items = []

        # results price and livable square meters are used to remove duplicate.
        for item in flat_list:
            for u_item in unique_items:
                if item not in unique_items:
                    if item["price"] != u_item["price"]:
                        if (
                            item["livable_square_meters"]
                            != u_item["livable_square_meters"]
                        ):
                            unique_items.append(item)

        return unique_items

    def get_insights(self, results):
        stats_selling = StatisticalInsights(results)
        price_mean_selling = stats_selling.calculate_mean_price()
        price_median_selling = stats_selling.calculate_median_price()
        logging.info(f"Selling mean price {price_median_selling}")
        logging.info(f"Selling median price {price_median_selling}")

        stats_renting = StatisticalInsights(results)
        price_mean_renting = stats_renting.calculate_mean_price()
        price_median_renting = stats_renting.calculate_median_price()
        logging.info(f"Renting mean price {price_mean_renting}")
        logging.info(f"Renting mean price {price_median_renting}")

        yield_rent_gross_median = StatisticalInsights().calculate_gross_yield_median(
            price_mean_renting, price_mean_selling
        )
        logging.info(f"Rent yield gross median {yield_rent_gross_median}")
