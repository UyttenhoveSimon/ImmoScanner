import plac
from ImmoScanner import ImmoScanner


@plac.pos('-c','--country', type=str, required=True,
    help='Country targeted by the research')

@plac.opt('-p','--postal_code', type=str,
    help='postal code targeted by the research')

@plac.opt('-ct','--city', type=str,
    help='city targeted by the research')

@plac.opt('-u','--url', type=str,
    help='url of targeted website')
def main():
"""
    Welcome to ImmoScanner, please enter:
    -country (mandatory)
    -postal_code (optional)
    -city (optional)
    -url (optional)
    Add at least either the postal code or the city.
    If url is provided, only the targeted website will be parsed, country must still be provided.
"""
if args.url is not None:
    ImmoScanner().research_real_estate_url(args)
elif (args.city is not None) or args.postal_code is not None:
    ImmoScanner().research_real_estate(args)

if __name__ == '__main__':
    plac.call(main)

