import sys
from cmd import Cmd

from Means.Research import Research
from Means.RealEstateResearch import RealEstateResearch
from Workers.Immoweb import Immoweb
from pprint import pprint
import logging
from Intellectuals.StatisticalInsights import StatisticalInsights
from Countries.Country import Country


class ImmoScanner():


    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)

    def research_real_estate(self, **params):
        """Enter arguments in that order 1)Country 2)Type (real estate...) 3)Postal code 4)Buy/Rent   """



        searches_immo_to_sell = RealEstateResearch(postal_code, city) # TODO: validate entries + research postal code or city name
        results_immoweb_to_sell = Immoweb().get_results(searches_immo_to_sell)

        good_stats_to_sell = StatisticalInsights(results_immoweb_to_sell)
        price_mean_to_sell = good_stats_to_sell.calculate_mean_price()
        price_median_to_sell = good_stats_to_sell.calculate_median_price()

        searches_immo_to_rent = RealEstateResearch(postal_code, city) # TODO: validate entries + research postal code or city name
        searches_immo_to_rent.rent_or_buy = "a-louer" # TODO : think how to orchestrate with another web site (deal with collisions) 
        results_immoweb_to_rent = Immoweb().get_results(searches_immo_to_rent)

        good_stats_to_rent = StatisticalInsights(results_immoweb_to_rent)
        price_mean_to_rent = good_stats_to_rent.calculate_mean_price()
        price_median_to_rent = good_stats_to_rent.calculate_median_price()

        yield_rent_gross_median = ((price_median_to_rent * 12) / price_median_to_sell) * 100
        logging.info(f'Rent yield gross median {yield_rent_gross_median}')
                     
    def research_real_estate_url(self, params):
        research = Research()
        research.url = params
        results_immoweb = Immoweb().get_results(research)
    

    def get_country(self, country):
        return Country().generate_country_given_name(country)
