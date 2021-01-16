from Countries.Country import Country
from Workers.Homegate import Homegate
from Workers.Comparis import Comparis


class Switzerland(Country):
    def __init__(self):
        self.websites = [Homegate(), Comparis()]

    def get_real_estate_websites(self):
        return self.websites
