"""Tell the listings that need work from those that are ready to live in.

No Belgian portal hands its building condition to a search page: immoweb's
cards carry a title and the energy certificate, immovlan's a full description
and the certificate. So the condition is read off those two, and every listing
keeps the reasons it was classed the way it was - a heuristic should show its
working, so a false positive is spotted at a glance.
"""

import re
import unicodedata

from ..Means.RealEstateResearch import ANY

#: something needs doing: a refresh, a new kitchen, an energy upgrade
WORKS = "works"
#: a full renovation, the stock a BRRRR investor is after
RENOVATE = "renovate"
CONDITIONS = (ANY, WORKS, RENOVATE)
#: a stronger condition outranks a weaker one when two copies of a listing meet
RANK = {"": 0, ANY: 0, WORKS: 1, RENOVATE: 2}

#: Walloon and Brussels certificates run A++ to G, Flemish ones A+ to F
EPC_LABELS = ("A++", "A+", "A", "B", "C", "D", "E", "F", "G")
EPC_FOR_RENOVATION = {"F", "G"}
EPC_FOR_WORKS = {"E"}

# Matched against accent-free, lower-cased text, so "à rénover" and the
# "a renover" agencies type without accents are one and the same.
RENOVATE_PHRASES = (
    r"a renover",
    r"a restaurer",
    r"a retaper",
    r"a rehabiliter",
    r"renovation (?:complete|totale|lourde|integrale)",
    r"entierement a (?:renover|refaire)",
    r"gros (?:travaux|oeuvre)",
    r"travaux (?:importants|lourds|de renovation)",
    r"(?:ideal|pour|special) investisseurs?",
    r"plateau a amenager",
    r"te renoveren",
    r"renovatiewoning",
    r"op te knappen",
    r"casco",
)
WORKS_PHRASES = (
    r"a rafraichir",
    r"rafraichissement",
    r"a moderniser",
    r"a remettre au gout du jour",
    r"(?:quelques|petits|des) travaux",
    r"travaux a prevoir",
    r"travaux de (?:finition|rafraichissement|mise en conformite)",
    r"op te frissen",
    r"te moderniseren",
)
# "aucun travaux à prévoir" advertises the opposite of what it contains
NEGATION = re.compile(r"(?:aucuns?|aucune|sans|pas de|nul besoin de|geen)\s+$")
NEGATION_WINDOW = 25

RENOVATE_PATTERN = re.compile(r"\b(?:" + "|".join(RENOVATE_PHRASES) + r")\b")
WORKS_PATTERN = re.compile(r"\b(?:" + "|".join(WORKS_PHRASES) + r")\b")


def normalise(text):
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents.casefold().replace("œ", "oe"))


def epc_label(text):
    """Pull a certificate label out of "C", "peb_c.png" or "WalloniaD"."""
    match = re.search(r"(A\+\+|A\+|[A-G])$", (text or "").strip().upper())
    return match.group(1) if match else ""


def phrases(pattern, text):
    found = []
    for match in pattern.finditer(text):
        before = text[max(0, match.start() - NEGATION_WINDOW) : match.start()]
        if NEGATION.search(before):
            continue
        if match.group(0) not in found:
            found.append(match.group(0))
    return found


def assess(item):
    """Return the condition a listing advertises, and the evidence for it."""
    text = normalise(item.description)
    heavy = phrases(RENOVATE_PATTERN, text)
    light = phrases(WORKS_PATTERN, text)

    reasons = [f"« {phrase} »" for phrase in heavy + light]
    epc = getattr(item, "epc", "")
    if epc in EPC_FOR_RENOVATION | EPC_FOR_WORKS:
        reasons.append(f"PEB {epc}")

    if heavy or epc in EPC_FOR_RENOVATION:
        return RENOVATE, reasons
    if light or epc in EPC_FOR_WORKS:
        return WORKS, reasons
    return "", reasons


def annotate(item):
    item.condition, item.condition_reasons = assess(item)
    return item


def merge(kept, duplicate):
    """Fold what a second portal knows about a listing into the copy kept.

    immoweb's card has only a title where immovlan prints the whole
    description, so the copy that survives de-duplication may be the one that
    says least about the state of the building.
    """
    if not kept.previous_price and duplicate.previous_price:
        kept.previous_price = duplicate.previous_price
    if not kept.epc and duplicate.epc:
        kept.epc = duplicate.epc
        # the certificate may be the only evidence there is
        absorb(kept, *assess(kept))
    absorb(kept, duplicate.condition, duplicate.condition_reasons)


def absorb(item, condition, reasons):
    if RANK[condition] > RANK[item.condition]:
        item.condition = condition
    for reason in reasons:
        if reason not in item.condition_reasons:
            item.condition_reasons.append(reason)


def meets(item, condition):
    """Does a listing need at least the asked amount of work?"""
    return RANK[item.condition] >= RANK[condition or ANY]
