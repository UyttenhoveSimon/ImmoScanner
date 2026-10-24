from .SchemaOrg import SchemaOrgWorker


class ImmoScout24(SchemaOrgWorker):
    """immobilienscout24.de, Germany's largest portal.

    Its searches are keyed by its own geography ids, so a search url copied
    from the site is followed instead (``scan --url``).
    """

    PAGE_PARAMETER = "pagenumber"

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "de-DE")
        kwargs.setdefault("timezone_id", "Europe/Berlin")
        super().__init__(**kwargs)
        self.domain_name = "immobilienscout24.de"
