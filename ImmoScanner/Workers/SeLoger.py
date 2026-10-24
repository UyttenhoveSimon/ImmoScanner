from .Aviv import AvivWorker


class SeLoger(AvivWorker):
    """seloger.com, in the same AVIV group as immowelt.de.

    Its searches are keyed by codes this scanner does not hold, so a search url
    copied from the site is followed instead (``scan --url``). It answered the
    first capture with a DataDome wall; its cards are assumed to be laid out
    as immowelt's are.
    """

    SEARCH_BY_PLACE = False
    VERIFIED = False

    def __init__(self, **kwargs):
        kwargs.setdefault("locale", "fr-FR")
        kwargs.setdefault("timezone_id", "Europe/Paris")
        super().__init__(**kwargs)
        self.domain_name = "seloger.com"
