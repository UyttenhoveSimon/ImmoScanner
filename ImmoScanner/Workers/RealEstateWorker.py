from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.Worker import Worker


class RealEstateWorker(Worker):

    def __init__(self):
        super().__init__()
        self.RealEstateResearchResult = [RealEstateResearchResult()]

    def get_results(self, recherche_immo):
        self.recherche = recherche_immo
        return [self.RealEstateResearchResult]


