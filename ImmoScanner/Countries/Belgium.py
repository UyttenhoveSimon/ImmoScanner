from Countries.Country import Country
from Workers.ImmoVlan import ImmoVlan
from Workers.Immoweb import Immoweb


class Belgium(Country):
    def __init__(self):
        self.websites = [ImmoVlan(), Immoweb()]

    def get_real_estate_websites(self):
        return self.websites
