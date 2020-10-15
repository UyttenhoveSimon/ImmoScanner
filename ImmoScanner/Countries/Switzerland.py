from ImmoScanner.Countries.Country import Country
from ImmoScanner.Workers.Homegate import Homegate


class Switzerland(Country):
    def __init__(self):
        self.websites = [Homegate()]

    def get_real_estate_websites(self):
        return self.websites
