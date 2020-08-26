import re

from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.RealEstateWorker import RealEstateWorker
from Means.RealEstateResearch import RealEstateResearch
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from price_parser import Price
import logging


class ImmoVlan(RealEstateWorker):

     def fill_empty_fields(self, real_estate_research: RealEstateResearch):
        if real_estate_research.rent_or_buy is None:
            real_estate_research.rent_or_buy = "a-vendre"

        if real_estate_research.type is None:
            real_estate_research.type = "maison"

        if real_estate_research.country is None:
            real_estate_research.country = "Belgique"

    def get_soupe(self, url):
        self.driver.get(url) # TODO : parfois echoue avec dns error, à gerer
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    def get_findings(self, real_estate_research: RealEstateResearch):
        real_estate_research_results = []

        self.fill_empty_fields(real_estate_research)

        url = self.url_builder(real_estate_research)
        logging.info(url)
        
        try:
            soup = self.get_soupe(url)
            nombre_pages = self.get_page_number(soup)

            for page in range(1, nombre_pages + 1):
                url = self.url_builder(real_estate_research, page)
                soup = self.get_soupe(url)
                findings = soup.find_all("article", {"card card--result card--xl"} )

                if not findings:
                    findings = soup.find_all("article", {"card card--result card--large"} )
                       
                for item in findings:
                    real_estate_research_results.append(self.extract_findings(item))

        finally:
            self.driver.close()
            return real_estate_research_results

    def get_result_id(self, result):
        return result['id'].split('_')[1]

    def get_result_description(self, result):
        if hasattr(result.contents[0].contents[8], 'text'):
            return result.contents[0].contents[8].text
        else:
            return ""

    def get_result_link(self, result):
        return result.contents[0].contents[2].contents[0]['href']

    def get_result_price(self, result):
        price = Price.fromstring(result.contents[0].contents[4].contents[0].contents[2].text.strip())
        return price.amount, price.currency
    
    def extract_findings(self, result):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.id = self.get_result_id(result)
        logging.debug('id: ' + real_estate_item.id)
      
        real_estate_item.description = self.get_result_description(result)
        logging.debug('texte: ' + real_estate_item.description)

        real_estate_item.url = self.get_result_link(result)
        logging.debug('lien: ' + real_estate_item.url)

        real_estate_item.price, real_estate_item.currency = self.get_result_price(result)
        logging.debug('price: ' + str(real_estate_item.price), 'currency: ' + real_estate_item.currency)

        return real_estate_item

    def url_builder(self, real_estate_research: RealEstateResearch, page = 1):
        if page != 1:
            return f"https://www.immovlan.be/fr/recherche/{real_estate_research.type_bien}/{real_estate_research.louer_acheter}/{real_estate_research.ville}/{real_estate_research.code_postal}?countries=BE&page={page}"

        if real_estate_research.url is not "":
            return real_estate_research.url # TODO Ajouter fonction pour chopper les parametres de l'url

        return f"https://www.immovlan.be/fr/recherche/{real_estate_research.type_bien}/{real_estate_research.louer_acheter}/{real_estate_research.ville}/{real_estate_research.code_postal}?countries=BE&page={page}"

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