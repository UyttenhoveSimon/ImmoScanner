from Means.ResultatsRecherche import ResultatsRecherche


class ResultatsRechercheImmo(ResultatsRecherche):
    
    def __init__(self):
        super().__init__()
        self.code_postal = ""
        self.type_bien = ""

