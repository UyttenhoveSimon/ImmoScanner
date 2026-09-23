"""A local, read-only web view onto an archive.

The standard library is enough here: the page is one file, the data is one
sqlite archive, and the audience is whoever is sitting at the machine. It
binds to the loopback address - the archive is yours, not the network's.
"""

import json
import logging
import pathlib
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .Explorer import Explorer

logger = logging.getLogger(__name__)

PAGE = pathlib.Path(__file__).parent / "page.html"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def answer(explorer, path, query):
    """Route one api path to the explorer. Returns the object to serialise."""
    if path == "/api/searches":
        return explorer.searches()

    if path == "/api/listings":
        return explorer.listings(
            search_key=query.get("search"),
            source=query.get("source"),
            sort=query.get("sort", "price"),
            limit=query.get("limit", 200),
        )

    if path == "/api/history":
        return explorer.price_history(query.get("platform", ""), query.get("id", ""))

    if path == "/api/movements":
        return explorer.movements(query.get("search", ""))

    return None


class Handler(BaseHTTPRequestHandler):
    archive_path = None
    server_version = "ImmoScanner"

    def log_message(self, format, *args):
        logger.debug(f"{self.address_string()} {format % args}")

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        query = {
            key: value
            for key, value in urllib.parse.parse_qsl(parsed.query)
            if value != ""
        }

        if parsed.path in ("/", "/index.html"):
            return self.send_bytes(PAGE.read_bytes(), "text/html; charset=utf-8")

        if not parsed.path.startswith("/api/"):
            return self.send_error(404)

        try:
            with Explorer(self.archive_path) as explorer:
                payload = answer(explorer, parsed.path, query)
        except Exception as error:
            logger.warning(f"{parsed.path} failed: {error}")
            return self.send_error(500, "the archive could not answer that")

        if payload is None:
            return self.send_error(404)

        self.send_bytes(
            json.dumps(payload, default=str).encode(), "application/json; charset=utf-8"
        )

    def send_bytes(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(archive_path, host=DEFAULT_HOST, port=DEFAULT_PORT):
    handler = type("BoundHandler", (Handler,), {"archive_path": str(archive_path)})
    return ThreadingHTTPServer((host, port), handler)


def serve(archive_path, host=DEFAULT_HOST, port=DEFAULT_PORT):
    if not pathlib.Path(archive_path).exists():
        raise FileNotFoundError(
            f"no archive at {archive_path}; run a scan with --store first"
        )

    server = build_server(archive_path, host, port)
    address = f"http://{host}:{server.server_address[1]}"
    print(f"exploring {archive_path} at {address} - ctrl-c to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.shutdown()
        server.server_close()
