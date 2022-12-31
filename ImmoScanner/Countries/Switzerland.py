from Countries.Country import Country
from Workers.Comparis import Comparis
from Workers.Homegate import Homegate


class Switzerland(Country):
    def __init__(self):
        self.websites = [Homegate(), Comparis()]

    def get_real_estate_websites(self):
        return self.websites
