from Means.ResearchResult import ResearchResult


class RealEstateResearchResult(ResearchResult):
    
    def __init__(self):
        super().__init__()
        self.code_postal = ""
        self.type_bien = ""

