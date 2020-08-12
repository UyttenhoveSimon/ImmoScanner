import sys
from cmd import Cmd

from Means.Recherche import Recherche
from Means.RechercheImmo import RechercheImmo
from Workers.Immoweb import Immoweb
from pprint import pprint
import logging
from Intellectuals.StatisticalInsights import StatisticalInsights


class Console(Cmd):
    intro = "Welcome to ImmoScanner"
    logging.basicConfig(level=logging.DEBUG)

    def do_research_immo(self, params):
        scanner = ImmoScanner()


    def do_research_immo_url(self, params):
        

if __name__ == '__main__':
    console = Console()
    console.prompt = '> '
    Console().cmdloop()
