import re
import logging
import time
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from price_parser import Price
from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.RealEstateWorker import RealEstateWorker
from Means.RealEstateResearch import RealEstateResearch


class ImmoVlan(RealEstateWorker):
    def __init__(self):
        super().__init__()
        self.domain_name = "immo.vlan.be"

    def fill_empty_fields(self, real_estate_research: RealEstateResearch):
        if real_estate_research.rent_or_buy is None:
            real_estate_research.rent_or_buy = "a-vendre"

        if real_estate_research.type is None:
            real_estate_research.type = "maison"

        if real_estate_research.country is None:
            real_estate_research.country = "Belgique"

    def get_findings(self, real_estate_research: RealEstateResearch):
        real_estate_research_results = []
        self.fill_empty_fields(real_estate_research)

        url = self.url_builder(real_estate_research)
        logging.info(url)


        try:
            soup = self.get_soupe(url)
            cookies_present = EC.presence_of_element_located((By.CSS_SELECTOR, "#didomi-notice-agree-button"))
            WebDriverWait(self.driver, 5).until(cookies_present).click()
                     
            pagination_present = EC.presence_of_element_located((By.CLASS_NAME, 'pagination'))
            WebDriverWait(self.driver, 5).until(pagination_present)
            # soup = self.get_soupe(self.driver.page_source)
            page_number = self.get_page_number()

            for page in range(1, page_number + 1):
                url = self.url_builder(real_estate_research, page)
                soup = self.get_soupe_driver()
                findings = soup.find_all("div", {"class", "pb-3 col-lg-12"})

                if not findings:
                    findings = soup.find_all(
                        "article", {"card card--result card--large"}
                    )

                for item in findings:
                    real_estate_research_results.append(self.extract_findings(item))

        finally:
            self.driver.close()
            return real_estate_research_results

    def get_result_id(self, result):
        return result["id"].split("_")[1]

    def get_result_description(self, result):
        if hasattr(result.contents[0].contents[8], "text"):
            return result.contents[0].contents[8].text
        else:
            return ""

    def get_result_link(self, result):
        return result.contents[0].contents[2].contents[0]["href"]

    def get_result_price(self, result):
        price = Price.fromstring(
            result.contents[0].contents[4].contents[0].contents[2].text.strip()
        )
        return price.amount, price.currency

    def extract_findings(self, result):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.id = self.get_result_id(result)
        logging.debug("id: " + real_estate_item.id)

        real_estate_item.description = self.get_result_description(result)
        logging.debug("texte: " + real_estate_item.description)

        real_estate_item.url = self.get_result_link(result)
        logging.debug("lien: " + real_estate_item.url)

        real_estate_item.price, real_estate_item.currency = self.get_result_price(
            result
        )
        logging.debug(
            "price: " + str(real_estate_item.price),
            "currency: " + real_estate_item.currency,
        )

        return real_estate_item

    def url_builder(self, real_estate_research: RealEstateResearch, page=1):
        if real_estate_research.url != "":
            return real_estate_research.url

        if (
            page == 1
        ): 
           return f"https://immo.vlan.be/fr/immobilier?transactiontypes={real_estate_research.rent_or_buy}&propertytypes={real_estate_research.type}&towns={real_estate_research.postal_code}-{real_estate_research.city.lower()}&noindex=1"

        return f"https://immo.vlan.be/fr/immobilier?transactiontypes={real_estate_research.rent_or_buy}&propertytypes={real_estate_research.type}&towns={real_estate_research.postal_code}-{real_estate_research.city.lower()}&countries=belgique&pageOffset={page}&noindex=1"

    def get_page_number(self):      
        page_number = self.driver.find_element_by_class_name('pagination').text.split('\n')[-1]
        
        try:
            return int(page_number)
        except :
            return 1

