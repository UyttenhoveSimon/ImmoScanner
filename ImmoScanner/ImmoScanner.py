import sys
import tldextract
from Means.Research import Research
from Means.RealEstateResearch import RealEstateResearch
from Workers.Immoweb import Immoweb
from pprint import pprint
import logging
from Intellectuals.StatisticalInsights import StatisticalInsights
from Countries.Country import Country
from Countries.CountryFactory import CountryFactory


class ImmoScanner:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)

    def research_real_estate(self, country_name, postal_code="", city=""):
        """Enter arguments in that order 1)Country 2)Type (real estate...) 3)Postal code 4)Buy/Rent   """

        country = CountryFactory().generate_country_given_name(name=country_name)
        import pdb
        pdb.set_trace()
        websites = list()
        websites = country.get_real_estate_websites()

        if websites is None:
            print(f"the country {country} input is not implemented.")

        if not postal_code:
            postal_code = country.fetch_city_given_postal_code(city)

        if not city:
            city = country.fetch_postal_code_given_city(postal_code)

        searches_immo_to_sell = RealEstateResearch(postal_code, city)

        results = list()
        for website in websites:
            results.append(website.get_results(searches_immo_to_sell))

        return results

    def research_real_estate_url(self, country, url):
        research = Research()
        research.url = url

        websites = list()
        country = CountryFactory().generate_country_given_name(name=country_name)
        websites = country.get_real_estate_websites()

        if websites is None:
            print(f"the country {country} input is not implemented.")

        results = list()
        parsed_uri = tldextract.extract(research.url)
        for website in websites:
            if parsed_uri.domain == website.domain_name:
                results.append(website.get_results(research))

        return results

    def get_insights(self, results):
        good_stats_to_sell = StatisticalInsights(results)
        price_mean_to_sell = good_stats_to_sell.calculate_mean_price()
        price_median_to_sell = good_stats_to_sell.calculate_median_price()
        logging.info(f"Price mean to sell {price_median_to_sell}")
        logging.info(f"Price median to sell {price_median_to_sell}")

        good_stats_to_rent = StatisticalInsights(results)
        price_mean_to_rent = good_stats_to_rent.calculate_mean_price()
        price_median_to_rent = good_stats_to_rent.calculate_median_price()
        logging.info(f"Price mean to sell {price_median_to_sell}")
        logging.info(f"price median to rent {price_median_to_rent}")

        yield_rent_gross_median = StatisticalInsights().calculate_gross_yield_median(
            price_mean_to_rent, price_mean_to_sell
        )
        logging.info(f"Rent yield gross median {yield_rent_gross_median}")
