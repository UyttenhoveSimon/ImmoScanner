from ..Workers.ImmoScout24 import ImmoScout24
from ..Workers.Immowelt import Immowelt
from ..Workers.Kleinanzeigen import Kleinanzeigen
from .Country import Country


class Germany(Country):
    CURRENCY_CODE = "EUR"
    LANGUAGE_CODES = ("de",)
    #: the Länder
    REGIONS = (
        "Baden-Württemberg",
        "Bayern",
        "Berlin",
        "Brandenburg",
        "Bremen",
        "Hamburg",
        "Hessen",
        "Mecklenburg-Vorpommern",
        "Niedersachsen",
        "Nordrhein-Westfalen",
        "Rheinland-Pfalz",
        "Saarland",
        "Sachsen",
        "Sachsen-Anhalt",
        "Schleswig-Holstein",
        "Thüringen",
    )

    def __init__(self):
        super().__init__()
        # kleinanzeigen and immowelt search a place by themselves; immoscout24
        # follows a search url copied from its site
        self.websites = [Kleinanzeigen(), ImmoScout24(), Immowelt()]

    def get_real_estate_websites(self):
        return self.websites
