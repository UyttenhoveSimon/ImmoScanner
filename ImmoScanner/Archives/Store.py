import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    platform TEXT NOT NULL,
    listing_id TEXT NOT NULL,
    search_key TEXT NOT NULL,
    url TEXT,
    description TEXT,
    type TEXT,
    source TEXT,
    postal_code TEXT,
    city TEXT,
    currency TEXT,
    price REAL,
    livable_square_meters INTEGER,
    bedrooms_number INTEGER,
    rooms_number REAL,
    latitude REAL,
    longitude REAL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (platform, listing_id)
);

CREATE TABLE IF NOT EXISTS prices (
    platform TEXT NOT NULL,
    listing_id TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    price REAL,
    PRIMARY KEY (platform, listing_id, seen_at)
);

CREATE INDEX IF NOT EXISTS listings_by_search ON listings (search_key, last_seen);
"""

COLUMNS = (
    "url",
    "description",
    "type",
    "source",
    "postal_code",
    "city",
    "currency",
    "price",
    "livable_square_meters",
    "bedrooms_number",
    "rooms_number",
    "latitude",
    "longitude",
)


@dataclass
class Report:
    """What one run changed, relative to what the archive already held."""

    new: list = field(default_factory=list)
    price_changes: list = field(default_factory=list)  # (result, previous price)
    gone: list = field(default_factory=list)
    unchanged: int = 0

    def summary(self):
        drops = sum(1 for _, before in self.price_changes if before is not None)
        return (
            f"{len(self.new)} new, {drops} repriced, "
            f"{len(self.gone)} gone, {self.unchanged} unchanged"
        )


class Store:
    """Archive of every listing seen, so a run can be compared with the last one.

    Without it a scan is a snapshot: new properties, price cuts and withdrawn
    listings - the things worth being told about - cannot be seen at all.
    """

    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def close(self):
        self.connection.close()

    @staticmethod
    def search_key(country, postal_code, type, rent_or_buy):
        return f"{country}/{postal_code}/{type}/{rent_or_buy}"

    def record(self, search_key, results, seen_at=None):
        # Microseconds, not seconds: two runs in the same second would share a
        # timestamp, collapsing their price history and hiding every withdrawal.
        seen_at = seen_at or datetime.now(timezone.utc).isoformat()
        report = Report()

        for result in results:
            if not result.id:
                continue

            key = (result.platform, str(result.id))
            stored = self.connection.execute(
                "SELECT price FROM listings WHERE platform = ? AND listing_id = ?", key
            ).fetchone()

            values = {column: getattr(result, column, None) for column in COLUMNS}
            values["price"] = float(result.price) if result.price else None

            if stored is None:
                report.new.append(result)
                self.connection.execute(
                    "INSERT INTO listings (platform, listing_id, search_key, "
                    f"{', '.join(COLUMNS)}, first_seen, last_seen) VALUES "
                    f"(?, ?, ?, {', '.join('?' * len(COLUMNS))}, ?, ?)",
                    (*key, search_key, *values.values(), seen_at, seen_at),
                )
            else:
                previous = stored["price"]
                if previous != values["price"]:
                    report.price_changes.append((result, previous))
                else:
                    report.unchanged += 1

                assignments = ", ".join(f"{column} = ?" for column in COLUMNS)
                self.connection.execute(
                    f"UPDATE listings SET search_key = ?, {assignments}, last_seen = ? "
                    "WHERE platform = ? AND listing_id = ?",
                    (search_key, *values.values(), seen_at, *key),
                )

            self.connection.execute(
                "INSERT OR REPLACE INTO prices (platform, listing_id, seen_at, price) "
                "VALUES (?, ?, ?, ?)",
                (*key, seen_at, values["price"]),
            )

        # Anything this search reached before and did not reach now is off the market.
        report.gone = self.connection.execute(
            "SELECT * FROM listings WHERE search_key = ? AND last_seen < ?",
            (search_key, seen_at),
        ).fetchall()

        self.connection.commit()
        logger.info(f"archive {search_key}: {report.summary()}")
        return report

    def price_history(self, platform, listing_id):
        return self.connection.execute(
            "SELECT seen_at, price FROM prices "
            "WHERE platform = ? AND listing_id = ? ORDER BY seen_at",
            (platform, str(listing_id)),
        ).fetchall()
