import sys
from cmd import Cmd
from argparse import ArgumentParser

from Means.Recherche import Recherche
from Means.RealEstateResearch import RealEstateResearch
from Workers.Immoweb import Immoweb
from pprint import pprint
import logging
from Intellectuals.StatisticalInsights import StatisticalInsights
  

class Console(Cmd):

    parser = argparse.ArgumentParser(description='Welcome to ImmoScanner')

    parser.add_argument(
        'Country', metavar='str', type=str,
        help='Country targeted by the research')

    parser.add_argument(
        'postal_code', metavar='str', type=str,
        help='postal code targeted by the research')

    parser.add_argument(
        'city', metavar='str', type=str,
        help='city targeted by the research')

    parser.add_argument(
        '--log', default=sys.stdout, type=argparse.FileType('w'),
        help='the file where the sum should be written')
    args = parser.parse_args()

    intro = "Welcome to ImmoScanner"
    logging.basicConfig(level=logging.DEBUG)

    def do_research_immo(self, params):
        scanner = ImmoScanner()


    def do_research_immo_url(self, params):
        

if __name__ == '__main__':
    console = Console()
    console.prompt = '> '
    Console().cmdloop()
