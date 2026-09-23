from .ResearchResult import ResearchResult

#: ~11 m of latitude; enough to tell two buildings apart, loose enough that two
#: portals geocoding the same address land on the same cell
COORDINATE_PRECISION = 4


class RealEstateResearchResult(ResearchResult):
    def __init__(self):
        super().__init__()
        self.postal_code = ""
        self.city = ""
        self.type = ""
        self.livable_square_meters = 0
        self.bedrooms_number = 0
        self.rooms_number = 0
        self.latitude = None
        self.longitude = None
        #: a new-build development sold as a group of units rather than one
        #: property: it has a price range, not a price, so it stays out of the
        #: statistics while still being reported
        self.is_project = False
        self.price_min = 0
        self.price_max = 0

    @property
    def price_per_square_meter(self):
        if not self.price or not self.livable_square_meters:
            return None
        return float(self.price) / self.livable_square_meters

    def fingerprint(self):
        """Identity of the *property*, as opposed to that of the advertisement.

        Every portal publishes a locality and the property's measurements, so
        this key can be compared across all of them. A development has neither
        a price nor a surface of its own, so it can only stand for itself.
        """
        if self.is_project:
            return ("project", self.platform, self.id)

        return (
            self.postal_code,
            int(self.price) if self.price else 0,
            int(self.livable_square_meters),
            int(self.bedrooms_number),
        )

    def geo_fingerprint(self):
        """Sharper identity for the portals that publish coordinates.

        immoweb and comparis geocode their listings; two advertisements for the
        same building land on the same cell even when their stated surface
        differs by a square metre. Returns ``None`` when the portal gives no
        position.
        """
        if self.latitude is None or self.longitude is None:
            return None
        return (
            round(self.latitude, COORDINATE_PRECISION),
            round(self.longitude, COORDINATE_PRECISION),
            int(self.price) if self.price else 0,
        )

    def __repr__(self):
        return (
            f"<{self.platform} {self.id} {self.price_text or self.price} "
            f"{self.currency} {self.livable_square_meters}m² "
            f"{self.bedrooms_number}ch {self.postal_code} {self.city}>"
        )
