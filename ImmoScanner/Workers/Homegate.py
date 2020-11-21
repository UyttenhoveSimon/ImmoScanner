import logging

from price_parser import Price
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from Means.RealEstateResearch import RealEstateResearch
from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.RealEstateWorker import RealEstateWorker


class Homegate(RealEstateWorker):
    def __init__(self):
        super().__init__()
        self.domain_name = "homegate.ch"

    def fill_empty_fields(self, real_estate_research: RealEstateResearch):
        if real_estate_research.rent_or_buy is None:
            real_estate_research.rent_or_buy = "acheter"

        if real_estate_research.type is None:
            real_estate_research.type = "biens-immobiliers"

        if real_estate_research.country is None:
            real_estate_research.country = "Switzerland"

    def get_findings(self, real_estate_research: RealEstateResearch):
        real_estate_research_results = []
        self.fill_empty_fields(real_estate_research)

        url = self.url_builder(real_estate_research)
        logging.info(url)

        try:
            soup = self.get_soupe(url)
       
            # pagination_present = EC.presence_of_element_located(
            #     (By.CLASS_NAME, "router-link-exact-active router-link-active")
            # )
            # WebDriverWait(self.driver, 10).until(pagination_present)
            # soup = self.get_soupe(self.driver.page_source)
            page_number = self.get_page_number(soup)

            for page in range(1, page_number + 1):
                url = self.url_builder(real_estate_research, page)
                soup = self.get_soupe(url)
                findings = soup.find_all("div", {"data-test", "result-list"})

                # if not findings:
                #     findings = soup.find_all(
                #         "article", {"card card--result card--large"}
                #     )

                for item in findings:
                    real_estate_research_results.append(self.extract_findings(item))

        finally:
            self.driver.close()
            return real_estate_research_results

    def get_result_id(self, result):
        return result.a["href"].split("/")[-1]

    def get_result_description(self, result):
        description = (
            result.find("p", class_="ListItem_data_18_z_").contents[0].text
        )
        if description is None:
            return ""
        else:
            return description

    def get_result_link(self, result):
        return self.domain_name + result.result.a["href"]

    # def get_posted_date(self, result):
    #     return self.domain_name + result.find_all("a")[1]["href"]

    def get_bedrooms_number(self, result):
        return result.find("p", class_="ListItem_data_18_z_").contents[0].text

    def get_livable_square_meters(self, result):
        return result.find("p", class_="ListItem_data_18_z_").contents[0].text

    def get_result_price(self, result):
        return Price.fromstring(result.find("p", class_="ListItem_data_18_z_").contents[0].text)

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
        if real_estate_research.url != "":
            return real_estate_research.url

        if page == 1:
            return f"https://www.homegate.ch/{real_estate_research.rent_or_buy}/biens-immobiliers/npa-{real_estate_research.postal_code}/liste-annonces"

        return f"https://www.homegate.ch/{real_estate_research.rent_or_buy}/biens-immobiliers/npa-{real_estate_research.postal_code}/liste-annonces?ep={page}"


    def get_page_number(self, soupe):
        page_number_text = soupe.find("div",class_="HgPaginationSelector_paginatorBox_15QHK ResultListPage_paginationHolder_3XZql").text
        breakpoint()
        ## text is 12...4 
        if "..." in page_number_text:
            return int(page_number_text.split(".")[-1])    

        ## text is 12 or 1
        try:
            return int(page_number_text) % 10
        except:
            return 1

