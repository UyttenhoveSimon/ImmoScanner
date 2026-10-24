import re

from .SchemaOrg import SchemaOrgWorker


class Pap(SchemaOrgWorker):
    """pap.fr, owners selling without an agent.

    Its searches are keyed by its own place ids ("-g439"), so a search url
    copied from the site is followed instead (``scan --url``). Pages are a
    path suffix, not a parameter: ".../vente-maisons-lyon-69-g43590-2".
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "fr-FR")
        kwargs.setdefault("timezone_id", "Europe/Paris")
        super().__init__(**kwargs)
        self.domain_name = "pap.fr"

    def url_builder(self, real_estate_research, page=1):
        url = super().url_builder(real_estate_research, page)
        base = re.sub(r"[?&]page=\d+", "", url).rstrip("?&")
        if page == 1:
            return base
        path, _, query = base.partition("?")
        path = re.sub(r"(-g\d+)(-\d+)?$", rf"\1-{page}", path)
        return f"{path}?{query}" if query else path
