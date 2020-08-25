import pycountry
import wikipedia

class Country():

    def __init__(self):
        self.alpha_2=""
        self.alpha_3=""
        self.numeric=""
        self.name=""
        self.official_name=""
        self.currency=""
        self.languages=[]
        self.websites=[]

    def generate_country_givent_name(self, name):
        country = pycountry.countries.get(name=name)
        self.alpha_2 = country.alpha_2
        self.alpha_3 = country.alpha_3
        self.numeric = country.numeric
        self.name = country.name
        self.official_name = country.official_name
        self.currency = country.currency
        self.languages = country.languages
        return country


    def fetch_city_given_postal_code(self, country):
        searches = wikipedia.search(country)
        for search in searches:
            if "City" in wikipedia.summary(search):
                return search
        return None


    def fetch_postal_code_given_city(self, postal_code):
        searches = wikipedia.search(postal_code)
        for search in searches:
            if "Postal Code" in wikipedia.summary(search):
                return search
        return None

