from Means.Research import Research


class RechercheImmo(Research):
    
    def __init__(self, code_postal: str, ville: str ): #type_bien, louer_acheter, pays --> arguments optionels ou bien a remplir ?
        super().__init__()
        self.type_bien = None
        self.louer_acheter = None
        self.pays = None
        self.ville = ville
        self.code_postal = code_postal
