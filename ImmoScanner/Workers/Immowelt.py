from .SchemaOrg import SchemaOrgWorker


class Immowelt(SchemaOrgWorker):
    """immowelt.de, which took in immonet.de's listings.

    Its searches are keyed by location codes this scanner does not hold, so a
    search url copied from the site is followed instead (``scan --url``).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "de-DE")
        kwargs.setdefault("timezone_id", "Europe/Berlin")
        super().__init__(**kwargs)
        self.domain_name = "immowelt.de"
