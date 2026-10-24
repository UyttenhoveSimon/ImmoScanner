from ..Workers.BienIci import BienIci
from ..Workers.Leboncoin import Leboncoin
from ..Workers.Pap import Pap
from ..Workers.SeLoger import SeLoger
from .Country import Country


class France(Country):
    CURRENCY_CODE = "EUR"
    LANGUAGE_CODES = ("fr",)
    #: the metropolitan régions, as bienici's place search knows them
    REGIONS = (
        "Auvergne-Rhône-Alpes",
        "Bourgogne-Franche-Comté",
        "Bretagne",
        "Centre-Val de Loire",
        "Corse",
        "Grand Est",
        "Hauts-de-France",
        "Île-de-France",
        "Normandie",
        "Nouvelle-Aquitaine",
        "Occitanie",
        "Pays de la Loire",
        "Provence-Alpes-Côte d'Azur",
    )

    def __init__(self):
        super().__init__()
        # bienici and leboncoin search a place by themselves; seloger and pap
        # follow a search url copied from their site
        self.websites = [BienIci(), Leboncoin(), SeLoger(), Pap()]

    def get_real_estate_websites(self):
        return self.websites
