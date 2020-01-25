from Moyens.Recherche import Recherche


class RechercheImmo(Recherche):
    
    def __init__(self, code_postal: str, ville: str, type_bien="maison", louer_acheter="a-vendre", pays="Belgique"):
        super().__init__()
        self.type_bien = type_bien
        self.louer_acheter = louer_acheter
        self.pays = pays
        self.ville = ville
        self.code_postal = code_postal