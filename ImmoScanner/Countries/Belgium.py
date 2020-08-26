from Countries.Country import Country
from Workers.Immoweb import Immoweb
from Workers.ImmoVlan import ImmoVlan

class Belgium(Country):

    def __init__(self):
        super().__init__()

    def get_real_estate_websites(self):
        self.websites= [
            Immoweb(),
            ImmoVlan()
        ]