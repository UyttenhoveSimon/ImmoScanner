import plac
from ImmoScanner import ImmoScanner


@plac.pos("--country", "Country targeted by the research", type=str)
@plac.opt("--postal_code", "postal code targeted by the research", type=str)
@plac.opt("--city", "city targeted by the research", type=str)
@plac.opt("--url", "url of targeted website", type=str)
@plac.flg('debug', "Enable debug mode")
def main(country, postal_code="", city="", url="", debug=False):
    """
    Welcome to ImmoScanner, please enter:
    -country (mandatory)
    -postal_code (optional)
    -city (optional)
    -url (optional)
    Add at least either the postal code or the city.
    If url is provided, only the targeted website will be parsed, country must still be provided.
    """

    if url is not None:
        ImmoScanner().research_real_estate_url(country=country, url=url)
    elif (city is not None) or (postal_code is not None):
        ImmoScanner().research_real_estate(
            country_name=country, city=city, postal_code=postal_code
        )


if __name__ == "__main__":
    plac.call(main)
