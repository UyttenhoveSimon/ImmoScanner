"""Read-only views over an archive, for the explorer to serve.

Kept apart from the http layer so the questions it answers can be asked - and
tested - without a socket. Every query is parameterised; nothing the browser
sends ever reaches sqlite as sql.
"""

import sqlite3
import statistics

#: how a listing may be ordered, mapped to the column it really sorts on
SORTS = {
    "price": "price",
    "surface": "livable_square_meters",
    "price_per_m2": "price / livable_square_meters",
    "seen": "last_seen",
    "city": "city",
}
DEFAULT_LIMIT = 200
MAX_LIMIT = 2000


class Explorer:
    def __init__(self, path):
        self.connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def close(self):
        self.connection.close()

    def rows(self, sql, parameters=()):
        return [dict(row) for row in self.connection.execute(sql, parameters)]

    def searches(self):
        """One entry per archived search, with the statistics that compare them.

        Medians are computed here rather than in sql: sqlite has no median, and
        an archive holds thousands of rows, not millions.
        """
        summaries = []
        for scope in self.rows(
            "SELECT search_key, COUNT(*) AS listings, MAX(last_seen) AS last_seen "
            "FROM listings GROUP BY search_key ORDER BY search_key"
        ):
            summaries.append({**scope, **self.statistics_for(scope["search_key"])})
        return summaries

    def statistics_for(self, search_key):
        priced = self.rows(
            "SELECT price, livable_square_meters AS surface FROM listings "
            "WHERE search_key = ? AND price > 0",
            (search_key,),
        )
        prices = [row["price"] for row in priced]
        ratios = [row["price"] / row["surface"] for row in priced if row["surface"]]

        return {
            "priced": len(prices),
            "median_price": statistics.median(prices) if prices else 0,
            "mean_price": statistics.mean(prices) if prices else 0,
            "first_quartile": quantile(prices, 0.25),
            "third_quartile": quantile(prices, 0.75),
            "median_price_per_m2": statistics.median(ratios) if ratios else 0,
        }

    def listings(self, search_key=None, source=None, sort="price", limit=DEFAULT_LIMIT):
        where, parameters = [], []
        if search_key:
            where.append("search_key = ?")
            parameters.append(search_key)
        if source:
            where.append("COALESCE(NULLIF(source, ''), platform) LIKE ?")
            parameters.append(f"%{source}%")

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        order = SORTS.get(sort, SORTS["price"])
        parameters.append(bounded(limit))

        return self.rows(
            "SELECT platform, listing_id, url, description, type, source, city, "
            "postal_code, price, currency, livable_square_meters, bedrooms_number, "
            "latitude, longitude, first_seen, last_seen "
            f"FROM listings {clause} "
            f"ORDER BY CASE WHEN price > 0 THEN 0 ELSE 1 END, {order} DESC "
            "LIMIT ?",
            parameters,
        )

    def price_history(self, platform, listing_id):
        return self.rows(
            "SELECT seen_at, price FROM prices "
            "WHERE platform = ? AND listing_id = ? ORDER BY seen_at",
            (platform, listing_id),
        )

    def movements(self, search_key):
        """Listings whose price changed, newest change first."""
        moved = []
        for row in self.rows(
            "SELECT platform, listing_id, url, city, price FROM listings "
            "WHERE search_key = ?",
            (search_key,),
        ):
            history = self.price_history(row["platform"], row["listing_id"])
            prices = [point["price"] for point in history if point["price"]]
            if len(set(prices)) < 2:
                continue
            moved.append({**row, "first_price": prices[0], "history": history})

        return sorted(moved, key=lambda row: row["price"] - row["first_price"])


def bounded(limit):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def quantile(values, fraction):
    """A plain nearest-rank quantile; statistics.quantiles needs two points."""
    if not values:
        return 0
    ordered = sorted(values)
    index = min(int(fraction * len(ordered)), len(ordered) - 1)
    return ordered[index]
