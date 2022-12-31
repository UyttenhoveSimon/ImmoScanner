import urllib.parse

import requests
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

    def fetch_city_given_postal_code(self, postal_code) -> list:
        """
        return following list:
        ['1', 'La Sarraz', '1315', 'Switzerland', 'Canton de Vaud', 'Morges District', 'La Sarraz\xa0\xa0\xa046.659/6.511\n\n', '', '\xa0\xa0\xa046.659/6.511', '']
        """
        search = requests.get(
            f"https://www.geonames.org/postalcode-search.html?q={postal_code}&country={self.alpha_2}"
        )
        soup = BeautifulSoup(search.text, "html.parser")
        print(soup)
        table = soup.find("table", {"class": "restable"})

        rows = list()
        for row in table.find_all("td"):
            rows.append(row.text)

        return rows[1]

        # 

    ## TODO deal when city has more than once postal code.
    def fetch_postal_code_given_city(self, city):
        """
        return list:
        # ['1', 'La Sarraz', '1315', 'Switzerland', 'Canton de Vaud', 'Morges District', 'La Sarraz\xa0\xa0\xa046.659/6.511\n\n', '', '\xa0\xa0\xa046.659/6.511', '']
        """
        city = urllib.parse.quote_plus(city)
        search = requests.get(
            f"https://www.geonames.org/postalcode-search.html?q={city}&country={self.alpha_2}"
        )
        soup = BeautifulSoup(search.text, "html.parser")
        print(soup)
        table = soup.find("table", {"class": "restable"})

        rows = list()
        for row in table.find_all("td"):
            rows.append(row.text)

        return rows[2]

    def get_real_estate_websites(self):
        pass
