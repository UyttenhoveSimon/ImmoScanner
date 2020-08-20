from Means.RealEstateResearchResult import RealEstateResearchResult
from Workers.Travailleur import Travailleur


class TravailleurImmo(Travailleur):

    def __init__(self):
        super().__init__()
        self.RealEstateResearchResult = [RealEstateResearchResult()]

    def obtiens_resultats(self, recherche_immo):
        self.recherche = recherche_immo
        return [self.RealEstateResearchResult]


