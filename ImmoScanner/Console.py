import sys
import argparse
import logging
from Means.Recherche import Recherche
from Means.RealEstateResearch import RealEstateResearch
from Workers.Immoweb import Immoweb
from pprint import pprint
from Intellectuals.StatisticalInsights import StatisticalInsights
  

class Console():

    def research_immo(self, args):
        scanner = ImmoScanner()


if __name__ == '__main__':
     parser = argparse.ArgumentParser(
        description=
        '''
        Welcome to ImmoScanner, please enter:
        -country (mandatory)
        -postal_code (optional)
        -city (optional)
        -url (optional)
        Add at least either the postal code or the city.
        If url is provided, only the targeted website will be parsed, country must still be provided.
        '''
        )

    parser.add_argument(
        '--country', metavar='str', type=str,
        help='Country targeted by the research')

    parser.add_argument(
        '--postal_code', metavar='str', type=str,
        help='postal code targeted by the research')

    parser.add_argument(
        '--city', metavar='str', type=str,
        help='city targeted by the research')

    parser.add_argument(
        '--url', metavar='str', type=str,
        help='city targeted by the research')

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
