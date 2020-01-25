from Moyens.ResultatsRechercheImmo import ResultatsRechercheImmo
from Travailleurs.Travailleur import Travailleur


class TravailleurImmo(Travailleur):

    def __init__(self):
        super().__init__()
        self.ResultatsRechercheImmo = [ResultatsRechercheImmo()]

    def obtiens_resultats(self, recherche_immo):
        self.recherche = recherche_immo
        return [self.ResultatsRechercheImmo]


