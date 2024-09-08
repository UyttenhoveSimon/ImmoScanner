from bs4 import BeautifulSoup
from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.Worker import Worker


class RealEstateWorker(Worker):
    def __init__(self):
        super().__init__()
        self.real_estate_research_result = [RealEstateResearchResult()]

    def get_first_half(self, list_):
        half = len(list_) // 2
        return list_[:half]

    def get_html(self, url):
        self.navigate(url)  # TODO : sometimes fails with dns error
        return self.page.content()

    def get_soupe(self, url):
        self.navigate(url)  # TODO : sometimes fails with dns error
        return self.get_page_source_soupe()

    def get_page_source_soupe(self):
        html = self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        return soup
