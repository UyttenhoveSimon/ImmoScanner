import pycountry
from Countries.Belgium import Belgium
from Countries.Switzerland import Switzerland


class CountryFactory:
    def __init__(self):
        self.dicCountries = {"Belgium": Belgium(), "Switzerland": Switzerland()}

    def generate_country_given_name(self, name):
        if name in self.dicCountries.keys():
            country = self.dicCountries[name]
        else:
            return None

        iso_country = pycountry.countries.get(name=name)
        country.alpha_2 = iso_country.alpha_2
        country.alpha_3 = iso_country.alpha_3
        country.numeric = iso_country.numeric
        country.name = iso_country.name
        country.official_name = iso_country.official_name
        country.currency = pycountry.currencies.get(numeric=country.numeric)
        country.languages = pycountry.languages.get(
            alpha_2=f"{country.alpha_2.lower()}"
        )
        return country
