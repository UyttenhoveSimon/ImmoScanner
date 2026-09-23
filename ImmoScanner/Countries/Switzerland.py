from ..Workers.Comparis import Comparis
from .Country import Country


class Switzerland(Country):
    CURRENCY_CODE = "CHF"
    LANGUAGE_CODES = ("de", "fr", "it", "rm")

    def __init__(self):
        super().__init__()
        # homegate.ch and immoscout24.ch are behind DataDome on every entry
        # point, including their apis; comparis aggregates both and names the
        # originating portal on each result.
        self.websites = [Comparis()]

    def get_real_estate_websites(self):
        return self.websites
