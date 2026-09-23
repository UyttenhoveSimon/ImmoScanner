from ..Workers.Comparis import Comparis
from .Country import Country


class Switzerland(Country):
    CURRENCY_CODE = "CHF"
    LANGUAGE_CODES = ("de", "fr", "it", "rm")
    #: the cantons, spelled the way comparis emits them on its own pages
    REGIONS = (
        "Appenzell Rhodes-Extérieures",
        "Appenzell Rhodes-Intérieures",
        "Argovie",
        "Bâle-Campagne",
        "Bâle-Ville",
        "Berne",
        "Fribourg",
        "Genève",
        "Glaris",
        "Grisons",
        "Jura",
        "Lucerne",
        "Neuchâtel",
        "Nidwald",
        "Obwald",
        "Saint-Gall",
        "Schaffhouse",
        # comparis does not know the French "Schwytz"
        "Schwyz",
        "Soleure",
        "Tessin",
        "Thurgovie",
        "Uri",
        "Valais",
        "Vaud",
        "Zoug",
        "Zurich",
    )

    def __init__(self):
        super().__init__()
        # homegate.ch and immoscout24.ch are behind DataDome on every entry
        # point, including their apis; comparis aggregates both and names the
        # originating portal on each result.
        self.websites = [Comparis()]

    def get_real_estate_websites(self):
        return self.websites
