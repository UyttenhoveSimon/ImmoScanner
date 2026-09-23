class ResearchResult:
    def __init__(self):
        self.url = ""
        self.description = ""
        self.price = 0
        self.price_text = ""
        self.price_obj = None
        self.id = ""
        self.currency = ""
        self.platform = ""
        #: portal the listing originally comes from, when the platform aggregates
        self.source = ""
        self.posted_date = ""

    def to_dict(self):
        return {key: value for key, value in vars(self).items() if key != "price_obj"}
