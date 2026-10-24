from __future__ import annotations

from .ResearchResult import Amount, ResearchResult

#: what identifies a property: postal code, price, surface, bedrooms - or a
#: development by its portal and id
Fingerprint = tuple[str, ...] | tuple[str, int, int, int]
#: rounded latitude, rounded longitude, price
GeoFingerprint = tuple[float, float, int]

#: ~11 m of latitude; enough to tell two buildings apart, loose enough that two
#: portals geocoding the same address land on the same cell
COORDINATE_PRECISION = 4


class RealEstateResearchResult(ResearchResult):
    def __init__(self) -> None:
        super().__init__()
        self.postal_code = ""
        self.city = ""
        self.type = ""
        self.livable_square_meters = 0
        #: the plot, where the portal publishes one; 0 means unknown
        self.land_square_meters = 0
        self.bedrooms_number = 0
        #: comparis counts half rooms
        self.rooms_number: float = 0
        self.latitude: float | None = None
        self.longitude: float | None = None
        #: a new-build development sold as a group of units rather than one
        #: property: it has a price range, not a price, so it stays out of the
        #: statistics while still being reported
        self.is_project = False
        self.price_min: Amount = 0
        self.price_max: Amount = 0
        #: energy certificate label ("A+" to "G"); empty when not published
        self.epc = ""
        #: the asking price before the portal's last reduction; 0 if none shown
        self.previous_price: Amount = 0
        #: "", "works" or "renovate", read off the description and certificate
        #: (see Intellectuals.Renovation), with the phrases that decided it
        self.condition = ""
        self.condition_reasons: list[str] = []

    @property
    def price_per_square_meter(self) -> float | None:
        if not self.price or not self.livable_square_meters:
            return None
        return float(self.price) / self.livable_square_meters

    def fingerprint(self) -> Fingerprint:
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

    def geo_fingerprint(self) -> GeoFingerprint | None:
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

    def __repr__(self) -> str:
        return (
            f"<{self.platform} {self.id} {self.price_text or self.price} "
            f"{self.currency} {self.livable_square_meters}m² "
            f"{self.bedrooms_number}ch {self.postal_code} {self.city}>"
        )
