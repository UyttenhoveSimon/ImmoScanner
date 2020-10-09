from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.Worker import Worker
from bs4 import BeautifulSoup


class RealEstateWorker(Worker):
    def __init__(self):
        super().__init__()
        self.real_estate_research_result = [RealEstateResearchResult()]

    def get_first_half(self, liste):
        half = len(liste) // 2
        return liste[:half]

    def get_html(self, url):
        self.driver.get(url)  # TODO : sometimes fails with dns error
        return self.driver.page_source

    def get_soupe(self, url):
        self.driver.get(url)  # TODO : sometimes fails with dns error
        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        return soup

    def get_soupe_driver(self):
        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        return soup
