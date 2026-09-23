from ..Workers.ImmoVlan import ImmoVlan
from ..Workers.Immoweb import Immoweb
from .Country import Country


class Belgium(Country):
    CURRENCY_CODE = "EUR"
    LANGUAGE_CODES = ("nl", "fr", "de")

    def __init__(self):
        super().__init__()
        self.websites = [ImmoVlan(), Immoweb()]

    def get_real_estate_websites(self):
        return self.websites
