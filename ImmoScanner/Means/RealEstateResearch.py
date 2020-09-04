from Means.Research import Research


class RealEstateResearch(Research):
    def __init__(
        self, postal_code: str, city: str
    ):  # type, rent_or_buy, country --> arguments optionels ou bien a remplir ?
        super().__init__()
        self.type = None
        self.rent_or_buy = None
        self.country = None
        self.city = city
        self.postal_code = postal_code
