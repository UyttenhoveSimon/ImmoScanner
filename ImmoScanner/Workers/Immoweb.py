import re

from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.RealEstateWorker import RealEstateWorker
from Means.RealEstateResearch import RealEstateResearch
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from price_parser import Price
import logging


class Immoweb(RealEstateWorker):

    def fill_empty_fields(self, recherche_immo: RealEstateResearch):
        if recherche_immo.louer_acheter is None:
            recherche_immo.louer_acheter = "a-vendre"

        if recherche_immo.type_bien is None:
            recherche_immo.type_bien = "maison"

        if recherche_immo.pays is None:
            recherche_immo.pays = "Belgique"

    def get_soupe(self, url):
        self.driver.get(url) # TODO : parfois echoue avec dns error, à gerer
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def get_results(self, recherche_immo: RealEstateResearch):
        resultats_recherche_immo = []

        self.fill_empty_fields(recherche_immo)

        url = self.creation_url(recherche_immo)
        logging.info(url)
        
        try:
            soup = self.get_soupe(url)
            nombre_pages = self.get_page_number(soup)

            for page in range(1, nombre_pages + 1):
                url = self.creation_url(recherche_immo, page)
                soup = self.get_soupe(url)
                resultats_valeurs = soup.find_all("article", {"card card--result card--xl"} )

                if not resultats_valeurs:
                    resultats_valeurs = soup.find_all("article", {"card card--result card--large"} )
                       
                for resultat in resultats_valeurs:
                    resultats_recherche_immo.append(self.extraction_resultats(resultat))

        finally:
            self.driver.close()
            return resultats_recherche_immo

    def get_result_id(self, resultat):
        return resultat['id'].split('_')[1]

    def get_result_description(self, resultat):
        if hasattr(resultat.contents[0].contents[8], 'text'):
            return resultat.contents[0].contents[8].text
        else:
            return ""

    def get_result_link(self, resultat):
        return resultat.contents[0].contents[2].contents[0]['href']

    def get_result_price(self, resultat):
        price = Price.fromstring(resultat.contents[0].contents[4].contents[0].contents[2].text.strip())
        return price.amount, price.currency
    
    def extraction_resultats(self, resultat):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.id = self.get_result_id(resultat)
        logging.debug('id: ' + real_estate_item.id)
      
        real_estate_item.description = self.get_result_description(resultat)
        logging.debug('texte: ' + real_estate_item.description)

        real_estate_item.url = self.get_result_link(resultat)
        logging.debug('lien: ' + real_estate_item.url)

        real_estate_item.price, real_estate_item.currency = self.get_result_price(resultat)
        logging.debug('price: ' + str(real_estate_item.price), 'currency: ' + real_estate_item.currency)

        return real_estate_item

    def creation_url(self, recherche_immo: RealEstateResearch, page = 1):
        if page != 1:
            return f"https://www.immoweb.be/fr/recherche/{recherche_immo.type_bien}/{recherche_immo.louer_acheter}/{recherche_immo.ville}/{recherche_immo.code_postal}?countries=BE&page={page}"

        if recherche_immo.url is not "":
            return recherche_immo.url # TODO Ajouter fonction pour chopper les parametres de l'url

        return f"https://www.immoweb.be/fr/recherche/{recherche_immo.type_bien}/{recherche_immo.louer_acheter}/{recherche_immo.ville}/{recherche_immo.code_postal}?countries=BE&page={page}"

    def get_page_number(self, soup):
        pagination = soup.find_all("a", {"pagination__link button button--text"}) 
        if not len(pagination) == 0:
            first_half = self.get_first_half(pagination) # pagination presente deux fois sur la page
            return int(first_half[-1].text.split('Page', 1)[1].strip())
        else:
            return 1

    def get_first_half(self, la_liste):
        half = len(la_liste) // 2
        return la_liste[:half]
