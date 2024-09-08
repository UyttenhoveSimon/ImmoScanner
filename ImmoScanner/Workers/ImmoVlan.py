import logging

from Means.RealEstateResearch import RealEstateResearch
from Means.RealEstateResearchResult import RealEstateResearchResult
from playwright.sync_api import sync_playwright
from price_parser import Price


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

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)

            try:
                page.click("#didomi-notice-agree-button")
                page.wait_for_selector(".pagination")

                page_number = self.get_page_number(page)

                for page_num in range(1, page_number + 1):
                    url = self.url_builder(real_estate_research, page_num)
                    page.goto(url)
                    findings = page.query_selector_all("div.pb-3.col-lg-12")

                    for item in findings:
                        real_estate_research_results.append(self.extract_findings(item))

            finally:
                browser.close()
                return real_estate_research_results

    def get_result_id(self, result):
        return result.query_selector("a").get_attribute("id")

    def get_result_description(self, result):
        description = result.query_selector(
            "p.grey-text.list-item-description"
        ).inner_text()
        return description if description else ""

    def get_result_link(self, result):
        return self.domain_name + result.query_selector_all("a")[1].get_attribute(
            "href"
        )

    # def get_posted_date(self, result):
    #     return self.domain_name + result.find_all("a")[1]["href"]

    def get_bedrooms_number(self, result):
        return (
            result.query_selector(
                "div.text-center.highlight-thumb.ml-2.mr-2.mb-2.NrOfBedrooms"
            )
            .inner_text()
            .split()[-1]
        )

    def get_livable_square_meters(self, result):
        return (
            result.query_selector(
                "div.text-center.highlight-thumb.ml-2.mr-2.mb-2.LivableSurface"
            )
            .inner_text()
            .split()[-2]
        )

    def get_result_price(self, result):
        return Price.fromstring(
            result.query_selector("strong.list-item-price").inner_text()
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
        real_estate_item.livable_square_meters = int(
            self.get_livable_square_meters(result)
        )

        return real_estate_item

    def url_builder(self, real_estate_research: RealEstateResearch, page=1):
        if real_estate_research.url != "":
            return real_estate_research.url

        if page == 1:
            return f"https://immo.vlan.be/fr/immobilier?transactiontypes={real_estate_research.rent_or_buy}&propertytypes={real_estate_research.type}&towns={real_estate_research.postal_code}-{real_estate_research.city.lower()}&noindex=1"

        return f"https://immo.vlan.be/fr/immobilier?transactiontypes={real_estate_research.rent_or_buy}&propertytypes={real_estate_research.type}&towns={real_estate_research.postal_code}-{real_estate_research.city.lower()}&countries=belgique&pageOffset={page}&noindex=1"

    def get_page_number(self, page):
        page_number = page.query_selector(".pagination").inner_text().split("\n")[-1]

        try:
            return int(page_number)
        except:
            return 1
