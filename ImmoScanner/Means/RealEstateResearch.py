from .Research import Research

# Portal-independent vocabulary; each worker maps these onto its own url scheme.
BUY = "buy"
RENT = "rent"

ANY = "any"
HOUSE = "house"
APARTMENT = "apartment"

TRANSACTIONS = (BUY, RENT)
PROPERTY_TYPES = (ANY, HOUSE, APARTMENT)


class RealEstateResearch(Research):
    def __init__(
        self,
        postal_code: str = "",
        city: str = "",
        type: str = ANY,
        rent_or_buy: str = BUY,
        country: str = None,
        url: str = "",
    ):
        super().__init__()
        self.url = url
        self.type = type
        self.rent_or_buy = rent_or_buy
        self.country = country
        self.city = city
        self.postal_code = postal_code
