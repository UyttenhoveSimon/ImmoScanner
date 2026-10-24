from ..Means.RealEstateResearch import ANY, APARTMENT, BUY, HOUSE, RENT
from .Aviv import AvivWorker

BASE_URL = "https://www.immowelt.de"
TRANSACTIONS = {BUY: "kaufen", RENT: "mieten"}
PROPERTY_TYPES = {ANY: "immobilien", HOUSE: "haeuser", APARTMENT: "wohnungen"}


class Immowelt(AvivWorker):
    """immowelt.de, which took in immonet.de's listings.

    A town is searched by name: /suche/berlin/wohnungen/kaufen redirects to
    immowelt's own coded search for it.
    """

    VERIFIED = False

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "de-DE")
        kwargs.setdefault("timezone_id", "Europe/Berlin")
        super().__init__(**kwargs)
        self.domain_name = "immowelt.de"

    def url_builder(self, real_estate_research, page=1):
        if real_estate_research.url:
            return super().url_builder(real_estate_research, page)
        place = self.slugify(real_estate_research.city)
        if not place:
            msg = f"{self.domain_name} searches a town by its name"
            raise ValueError(msg)
        url = (
            f"{BASE_URL}/suche/{place}/{PROPERTY_TYPES[real_estate_research.type]}"
            f"/{TRANSACTIONS[real_estate_research.rent_or_buy]}"
        )
        return url if page == 1 else f"{url}?page={page}"
