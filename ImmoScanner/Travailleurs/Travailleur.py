from selenium import webdriver
import selenium.webdriver.common.by
from selenium.webdriver.firefox.options import Options
from Moyens.ResultatsRecherche import ResultatsRecherche
import logging


class Travailleur:

    def __init__(self):
        options = Options()
        if logging.root.level > logging.DEBUG:
            options.headless = True

        self.driver = webdriver.Firefox(options=options)
        self.driver.set_page_load_timeout(60)
        self.ResultatsRecherche = [ResultatsRecherche()]

    def obtiens_resultats(self, recherche):
        self.recherche = recherche
        return [self.ResultatsRecherche]
