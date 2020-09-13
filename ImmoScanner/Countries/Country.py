import pycountry
import requests
import urllib.parse
from bs4 import BeautifulSoup


class Country:
    def __init__(self):
        self.alpha_2 = ""
        self.alpha_3 = ""
        self.numeric = ""
        self.name = ""
        self.official_name = ""
        self.currency = ""
        self.languages = []
        self.websites = []

    def generate_country_given_name(self, name):
        country = pycountry.countries.get(name=name)
        self.alpha_2 = country.alpha_2
        self.alpha_3 = country.alpha_3
        self.numeric = country.numeric
        self.name = country.name
        self.official_name = country.official_name
        self.currency = country.currency
        self.languages = country.languages
        return country

    def fetch_city_given_postal_code(self, postal_code):
        search = requests.get(
            "https://www.geonames.org/postalcode-search.html?q={postal_code}&country=CH"
        )
        soup = BeautifulSoup(search.text, "html.parser")
        print(soup)
        table = soup.find("table", {"class": "restable"})

        rows = list()
        for row in table.find_all("td"):
            rows.append(row.text)

        return rows[1]

        # ['1', 'La Sarraz', '1315', 'Switzerland', 'Canton de Vaud', 'Morges District', 'La Sarraz\xa0\xa0\xa046.659/6.511\n\n', '', '\xa0\xa0\xa046.659/6.511', '']
        #

    def fetch_postal_code_given_city(self, city):
        city = urllib.parse.quote_plus(city)
        search = requests.get(
            "https://www.geonames.org/postalcode-search.html?q={city}&country=CH"
        )
        soup = BeautifulSoup(search.text, "html.parser")
        print(soup)
        table = soup.find("table", {"class": "restable"})

        rows = list()
        for row in table.find_all("td"):
            rows.append(row.text)
