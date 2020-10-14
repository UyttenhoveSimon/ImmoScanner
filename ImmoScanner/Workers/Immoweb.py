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
    def __init__(self):
        super().__init__()
        self.domain_name = "immoweb.be"

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
            nombre_pages = self.get_page_number(soup)

            for page in range(1, nombre_pages + 1):
                url = self.url_builder(real_estate_research, page)
                soup = self.get_soupe(url)
                findings = soup.find_all("article", {"card card--result card--xl"})

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

    # def get_posted_date(self, result):
    #     return self.domain_name + result.find_all("a")[1]["href"]

    def get_bedrooms_number(self, result):
        return (
            result.find(
                "p",
                class_="card__information card--result__information card__information--property",
            )
            .contents[0]
            .text.split()[0]
        )

    def get_livable_square_meters(self, result):
        return re.findall(
            r"\d+",
            result.find(
                "p",
                class_="card__information card--result__information card__information--property",
            ).contents[1],
        )[0]

    def get_result_price(self, result):
        return Price.fromstring(
            result.contents[0].contents[4].contents[0].contents[2].text.strip()
        )

    def extract_findings(self, result):
        real_estate_item = RealEstateResearchResult()

        real_estate_item.id = self.get_result_id(result)
        logging.debug(f"id: {real_estate_item.id}")

        real_estate_item.description = self.get_result_description(result)
        logging.debug(f"text: {real_estate_item.description}")

        real_estate_item.url = self.get_result_link(result)
        logging.debug(f"lien: {real_estate_item.url}")

        real_estate_item.price_obj = self.get_result_price(result)
        real_estate_item.price = real_estate_item.price_obj.amount
        real_estate_item.currency = real_estate_item.price_obj.currency
        real_estate_item.price_text = real_estate_item.price_obj.amount_text

        logging.debug(f"currency: {real_estate_item.currency}")
        logging.debug(f"price:  {real_estate_item.price_text}")

        real_estate_item.platform = self.domain_name

        real_estate_item.bedrooms_number = int(self.get_bedrooms_number(result))
        real_estate_item.livable_square_meters + int(
            self.get_livable_square_meters(result)
        )

        return real_estate_item

    def url_builder(self, real_estate_research: RealEstateResearch, page=1):
        if page != 1:
            return f"https://www.immoweb.be/fr/recherche/{real_estate_research.type}/{real_estate_research.rent_or_buy}/{real_estate_research.city}/{real_estate_research.postal_code}?countries=BE&page={page}"

        if real_estate_research.url != "":
            return real_estate_research.url

        return f"https://www.immoweb.be/fr/recherche/{real_estate_research.type}/{real_estate_research.rent_or_buy}/{real_estate_research.city}/{real_estate_research.postal_code}?countries=BE&page={page}"

    def get_page_number(self, soup):
        pagination = soup.find_all("a", {"pagination__link button button--text"})
        if not len(pagination) == 0:
            first_half = self.get_first_half(
                pagination
            )  # pagination is present two times on the page
            return int(first_half[-1].text.split("Page", 1)[1].strip())
        else:
            return 1
