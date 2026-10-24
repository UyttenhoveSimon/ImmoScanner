"""Reading a listing's condition off its description and energy certificate."""

import pytest

from ImmoScanner.ImmoScanner import ImmoScanner
from ImmoScanner.Intellectuals import Renovation
from ImmoScanner.Intellectuals.Renovation import RENOVATE, WORKS
from ImmoScanner.Means.RealEstateResearchResult import RealEstateResearchResult
from ImmoScanner.Workers.ImmoVlan import ImmoVlan
from ImmoScanner.Workers.Immoweb import Immoweb


def listing(description="", epc="", **extra):
    item = RealEstateResearchResult()
    item.description, item.epc = description, epc
    item.platform, item.id = "immoweb.be", extra.pop("listing_id", "1")
    item.price, item.livable_square_meters = 200000, 100
    item.postal_code = "4000"
    for name, value in extra.items():
        setattr(item, name, value)
    return item


class TestAssess:
    @pytest.mark.parametrize(
        "description",
        [
            "Maison 5 CH de ± 140 m² avec jardin, à rénover",
            "MAISON A RENOVER ENTIEREMENT",
            "Immeuble nécessitant une rénovation complète",
            "Idéal investisseur, gros travaux",
            "Gros œuvre à prévoir",
            "Woning te renoveren met tuin",
        ],
    )
    def test_heavy_work_is_a_renovation(self, description):
        condition, reasons = Renovation.assess(listing(description))
        assert condition == RENOVATE
        assert reasons

    @pytest.mark.parametrize(
        "description",
        [
            "Appartement à rafraîchir",
            "Maison saine, quelques travaux de finition",
            "Travaux à prévoir en cuisine",
            "Appartement op te frissen",
        ],
    )
    def test_light_work_is_works(self, description):
        assert Renovation.assess(listing(description))[0] == WORKS

    @pytest.mark.parametrize(
        "description",
        [
            "Maison entièrement rénovée en 2021",
            "Superbe villa récemment rénovée",
            "Aucuns travaux à prévoir, emménageable de suite",
            "Appartement sans travaux",
            "",
        ],
    )
    def test_a_finished_property_needs_nothing(self, description):
        assert Renovation.assess(listing(description))[0] == ""

    def test_a_poor_certificate_alone_means_renovation(self):
        condition, reasons = Renovation.assess(listing("Belle maison", epc="G"))
        assert (condition, reasons) == (RENOVATE, ["PEB G"])

    def test_an_e_certificate_means_works(self):
        assert Renovation.assess(listing(epc="E"))[0] == WORKS

    def test_a_good_certificate_adds_nothing(self):
        assert Renovation.assess(listing(epc="B")) == ("", [])

    @pytest.mark.parametrize(
        ("raw", "label"),
        [
            ("C", "C"),
            ("WalloniaD", "D"),
            ("FlandersA+", "A+"),
            ("peb_g", "G"),
            ("", ""),
            (None, ""),
            ("unknown", ""),
        ],
    )
    def test_certificate_labels(self, raw, label):
        assert Renovation.epc_label(raw) == label


class TestMerge:
    def test_the_kept_copy_learns_the_condition_of_its_duplicate(self):
        scanner = ImmoScanner()
        terse = listing("Maison 3 chambres", listing_id="1")
        verbose = listing(
            "Maison 3 chambres à rénover", listing_id="2", platform="immovlan.be"
        )

        (kept,) = scanner.duplicate_finder([[terse], [verbose]])

        assert kept is terse
        assert kept.condition == RENOVATE
        assert kept.condition_reasons == ["« a renover »"]

    def test_the_certificate_is_borrowed_and_counts(self):
        scanner = ImmoScanner()
        bare = listing("Maison", listing_id="1")
        labelled = listing("Maison", epc="F", listing_id="2", platform="immovlan.be")

        (kept,) = scanner.duplicate_finder([[bare], [labelled]])

        assert (kept.epc, kept.condition) == ("F", RENOVATE)

    def test_a_previous_price_is_borrowed(self):
        scanner = ImmoScanner()
        first = listing(listing_id="1")
        second = listing(listing_id="2", platform="immovlan.be", previous_price=1)

        (kept,) = scanner.duplicate_finder([[first], [second]])

        assert kept.previous_price == 1


class TestFilter:
    def test_each_level_keeps_what_needs_at_least_that_much(self):
        findings = [
            listing("à rénover", listing_id="a"),
            listing("à rafraîchir", listing_id="b"),
            listing("rénovée", listing_id="c"),
        ]
        for item in findings:
            Renovation.annotate(item)

        def ids(condition):
            return [i.id for i in ImmoScanner.filter_by_condition(findings, condition)]

        assert ids("any") == ["a", "b", "c"]
        assert ids(WORKS) == ["a", "b"]
        assert ids(RENOVATE) == ["a"]


class TestWorkers:
    def test_immoweb_reads_the_certificate(self, soup_of):
        immoweb = Immoweb()
        cards = soup_of("immoweb_search.html").select(immoweb.CARD_SELECTOR)
        results = [immoweb.extract_findings(card) for card in cards]
        first = next(r for r in results if r.id == "21803099")

        assert first.epc == "C"
        assert Renovation.assess(first)[0] == RENOVATE  # "... à rénover"

    def test_immovlan_reads_the_certificate_watermark(self, soup_of):
        immovlan = ImmoVlan()
        card = soup_of("immovlan_search.html").select(immovlan.CARD_SELECTOR)[0]
        assert immovlan.extract_findings(card).epc == "D"

    def test_immovlan_without_a_watermark(self, soup_of):
        immovlan = ImmoVlan()
        card = soup_of("immovlan_search.html").select(immovlan.CARD_SELECTOR)[0]
        for watermark in card.select(".v3-epc-watermark"):
            watermark.decompose()
        assert immovlan.get_epc(card) == ""


class TestEdgeCases:
    def test_a_dutch_negation_is_read_too(self):
        assert (
            Renovation.assess(listing("Woning met geen werken, op te frissen"))[0]
            == WORKS
        )
        assert Renovation.assess(listing("geen op te frissen"))[0] == ""

    def test_a_phrase_repeated_is_one_reason(self):
        _, reasons = Renovation.assess(listing("À rénover. Vraiment à rénover !"))
        assert reasons == ["« a renover »"]

    def test_heavy_and_light_phrases_both_show(self):
        condition, reasons = Renovation.assess(
            listing("À rénover, ou au moins à rafraîchir", epc="F")
        )
        assert condition == RENOVATE
        assert reasons == ["« a renover »", "« a rafraichir »", "PEB F"]

    def test_merging_twice_keeps_the_strongest_and_every_reason(self):
        kept = Renovation.annotate(listing("Maison", listing_id="1"))
        works = Renovation.annotate(listing("à rafraîchir", listing_id="2"))
        heavy = Renovation.annotate(listing("à rénover", listing_id="3"))

        Renovation.merge(kept, heavy)
        Renovation.merge(kept, works)

        assert kept.condition == RENOVATE
        assert kept.condition_reasons == ["« a renover »", "« a rafraichir »"]

    def test_a_listing_without_a_condition_meets_only_any(self):
        item = listing()
        assert Renovation.meets(item, "any") and Renovation.meets(item, "")
        assert not Renovation.meets(item, WORKS)


class TestImmowebPriceCut:
    def test_the_old_price_of_a_reduced_listing_is_kept(self, soup_of):
        import json

        immoweb = Immoweb()
        card = soup_of("immoweb_search.html").select(immoweb.CARD_SELECTOR)[0]
        component = card.find(attrs={":classified": True})
        classified = json.loads(component[":classified"])
        classified["transaction"]["sale"]["oldPrice"] = 219000

        item = immoweb.extract_from_classified(card, classified)

        assert item.previous_price == 219000

    def test_a_card_without_a_transaction_has_no_certificate(self, soup_of):
        immoweb = Immoweb()
        card = soup_of("immoweb_search.html").select(immoweb.CARD_SELECTOR)[0]
        item = immoweb.extract_from_classified(card, {"id": 1})
        assert (item.epc, item.previous_price) == ("", 0)
