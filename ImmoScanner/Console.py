import sys
from cmd import Cmd

from Means.Recherche import Recherche
from Means.RechercheImmo import RechercheImmo
from Workers.Immoweb import Immoweb
from pprint import pprint
import logging
from Intellectuals.StatisticalInsights import StatisticalInsights


class Console(Cmd):
    intro = "Welcome in ImmoScanner"
    logging.basicConfig(level=logging.DEBUG)

    def do_research_immo(self, params):
        """Enter arguments in that order 1)Country 2)Type (real estate...) 3)Postal code 4) Buy/Rent   """
      
        postal_code, city = params.split()
        searches_immo_to_sell = RechercheImmo(postal_code, city) # TODO: validate entries + research postal code or city name
        results_immoweb_to_sell = Immoweb().get_results(searches_immo_to_sell)

        good_stats_to_sell = StatisticalInsights(results_immoweb_to_sell)
        price_mean_to_sell = good_stats_to_sell.calculate_mean_price()
        price_median_to_sell = good_stats_to_sell.calculate_median_price()

        searches_immo_to_rent = RechercheImmo(postal_code, city) # TODO: validate entries + research postal code or city name
        searches_immo_to_rent.louer_acheter = "a-louer" # TODO : think how to orchestrate with another web site (deal with collisions) 
        results_immoweb_to_rent = Immoweb().get_results(searches_immo_to_rent)

        good_stats_to_rent = StatisticalInsights(results_immoweb_to_rent)
        price_mean_to_rent = good_stats_to_rent.calculate_mean_price()
        price_median_to_rent = good_stats_to_rent.calculate_median_price()

        yield_rent_gross_median = ((price_median_to_rent * 12) / price_median_to_sell) * 100
        logging.info(f'Rendement locatif brut median {yield_rent_gross_median}')
                     
    def do_research_immo_url(self, params):
        recherche = Recherche()
        recherche.url = params
        results_immoweb = Immoweb().get_results(recherche)


if __name__ == '__main__':
    console = Console()
    console.prompt = '> '
    Console().cmdloop()
