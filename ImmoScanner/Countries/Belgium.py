from ImmoScanner.Countries.Country import Country
from ImmoScanner.Workers.Immoweb import Immoweb
from ImmoScanner.Workers.ImmoVlan import ImmoVlan


class Belgium(Country):
    def __init__(self):
        self.websites = [ImmoVlan(), Immoweb()]

    def get_real_estate_websites(self):
        return self.websites
