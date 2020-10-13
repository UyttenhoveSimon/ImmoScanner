from Countries.Country import Country
from Workers.Immoweb import Immoweb
from Workers.ImmoVlan import ImmoVlan


class Belgium(Country):
    def get_real_estate_websites(self):
        self.websites = [ImmoVlan(), Immoweb()]
        return self.websites
