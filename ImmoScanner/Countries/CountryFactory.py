import logging

import pycountry

from .Belgium import Belgium
from .Switzerland import Switzerland

logger = logging.getLogger(__name__)


class CountryFactory:
    def __init__(self):
        self.countries = {"Belgium": Belgium, "Switzerland": Switzerland}

    def generate_country_given_name(self, name):
        country_class = self.countries.get(name)
        if country_class is None:
            logger.error(f"the country {name} is not implemented")
            return None

        country = country_class()

        iso_country = pycountry.countries.get(name=name)
        country.alpha_2 = iso_country.alpha_2
        country.alpha_3 = iso_country.alpha_3
        country.numeric = iso_country.numeric
        country.name = iso_country.name
        country.official_name = getattr(iso_country, "official_name", iso_country.name)

        # ISO 3166 country codes and ISO 4217 currency codes do not share a
        # numbering, and a country code is not a language code, so both are
        # declared by the country subclass rather than derived from alpha_2.
        country.currency = pycountry.currencies.get(alpha_3=country_class.CURRENCY_CODE)
        country.languages = [
            pycountry.languages.get(alpha_2=code)
            for code in country_class.LANGUAGE_CODES
        ]
        return country
