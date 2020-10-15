from ImmoScanner.Means.ResearchResult import ResearchResult


class RealEstateResearchResult(ResearchResult):
    def __init__(self):
        super().__init__()
        self.postal_code = ""
        self.type = ""
        self.livable_square_meters = 0
        self.bedrooms_number = 0
        self.rooms_number = 0
