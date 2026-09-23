"""Runs a scan asked for from the page, and reports where it got to.

A scan takes tens of seconds, so the page cannot wait on it: it asks for one,
then polls. One runs at a time - the portals are already scanned in parallel
inside a scan, and stacking scans on top of that would only get the scanner
noticed.
"""

import logging
import threading

from ..Archives.Store import Store
from ..ImmoScanner import ImmoScanner
from ..Means.RealEstateResearch import ANY, BUY, PROPERTY_TYPES, TRANSACTIONS

logger = logging.getLogger(__name__)

IDLE, RUNNING, DONE, FAILED = "idle", "running", "done", "failed"


class Busy(RuntimeError):
    """A scan is already under way."""


class ScanRunner:
    def __init__(self, archive_path, scanner=None, store=None):
        self.archive_path = archive_path
        self.scanner = scanner or ImmoScanner()
        self.store = store or Store
        self.lock = threading.Lock()
        self.thread = None
        self.state = {"state": IDLE}

    def status(self):
        with self.lock:
            return dict(self.state)

    def start(self, country, postal_code="", city="", type=ANY, rent_or_buy=BUY):
        if not (postal_code or city):
            raise ValueError("a postal code or a city is needed")
        if type not in PROPERTY_TYPES:
            raise ValueError(f"unknown property type {type}")
        if rent_or_buy not in TRANSACTIONS:
            raise ValueError(f"unknown transaction {rent_or_buy}")

        with self.lock:
            if self.state["state"] == RUNNING:
                raise Busy(f"already scanning {self.state.get('asked')}")
            self.state = {
                "state": RUNNING,
                "asked": postal_code or city,
                "country": country,
                "type": type,
                "rent_or_buy": rent_or_buy,
            }
            # What is returned is the request being accepted, not a reading of
            # the state: a fast scan can finish before the caller sees it.
            accepted = dict(self.state)

        self.thread = threading.Thread(
            target=self.run,
            args=(country, postal_code, city, type, rent_or_buy),
            daemon=True,
        )
        self.thread.start()
        return accepted

    def run(self, country, postal_code, city, type, rent_or_buy):
        try:
            results = self.scanner.research_real_estate(
                country_name=country,
                postal_code=postal_code,
                city=city,
                type=type,
                rent_or_buy=rent_or_buy,
            )
            findings = self.scanner.duplicate_finder(results)

            with self.store(self.archive_path) as archive:
                key = archive.search_key(
                    country, postal_code or city, type, rent_or_buy
                )
                report = archive.record(key, findings)

            self.finish(
                {
                    "state": DONE,
                    "search_key": key,
                    "scanned": sum(len(group) for group in results),
                    "listings": len(findings),
                    "summary": report.summary(),
                }
            )
        except Exception as error:
            logger.warning(f"scan of {postal_code or city} failed: {error}")
            self.finish({"state": FAILED, "error": str(error)})

    def finish(self, state):
        with self.lock:
            self.state = {**self.state, **state}
