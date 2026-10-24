from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from price_parser import Price

#: what the portals hand over: an int from a JSON payload, a Decimal from
#: price_parser, nothing at all when a price is "on request"
Amount = int | float | Decimal | None


class ResearchResult:
    def __init__(self) -> None:
        self.url = ""
        self.description = ""
        self.price: Amount = 0
        self.price_text = ""
        self.price_obj: Price | None = None
        self.id = ""
        self.currency = ""
        self.platform = ""
        #: portal the listing originally comes from, when the platform aggregates
        self.source = ""
        self.posted_date = ""

    @property
    def price_value(self) -> float:
        """The price as a plain number; 0 when the portal gave none."""
        return float(self.price) if self.price else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in vars(self).items() if key != "price_obj"}
