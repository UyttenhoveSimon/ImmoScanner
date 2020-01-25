from selenium import webdriver
import selenium.webdriver.common.by
from selenium.webdriver.firefox.options import Options

from Moyens.ResultatsRecherche import ResultatsRecherche


class Travailleur:

    def __init__(self):
        options = Options()
        # options.headless = True
        self.driver = webdriver.Firefox(options=options)
        self.ResultatsRecherche = [ResultatsRecherche()]

    def obtiens_resultats(self, recherche):
        self.recherche = recherche
        return [self.ResultatsRecherche]
