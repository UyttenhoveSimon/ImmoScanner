import sys
import argparse
import logging
from pprint import pprint
from Means.Recherche import Recherche
from Means.RealEstateResearch import RealEstateResearch
from Workers.Immoweb import Immoweb
from ImmoScanner import ImmoScanner
from Intellectuals.StatisticalInsights import StatisticalInsights
  

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
    '-c','--country', metavar='str', type=str, required=True,
    help='Country targeted by the research')

parser.add_argument(
    '-p','--postal_code', metavar='str', type=str,
    help='postal code targeted by the research')

parser.add_argument(
    '-ct','--city', metavar='str', type=str,
    help='city targeted by the research')

parser.add_argument(
    '-u','--url', metavar='str', type=str,
    help='city targeted by the research')

args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG)

if args.url is not None:
    ImmoScanner().research_real_estate_url(args)
elif (args.city is not None) or args.postal_code is not None:
    ImmoScanner().research_real_estate(args)



