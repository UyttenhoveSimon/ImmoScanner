from .SchemaOrg import SchemaOrgWorker


class SeLoger(SchemaOrgWorker):
    """seloger.com, read through the schema.org list on its result pages.

    Its searches are keyed by INSEE codes this scanner does not hold, so a
    search url copied from the site is followed instead (``scan --url``).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "fr-FR")
        kwargs.setdefault("timezone_id", "Europe/Paris")
        super().__init__(**kwargs)
        self.domain_name = "seloger.com"
