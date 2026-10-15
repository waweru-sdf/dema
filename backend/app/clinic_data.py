"""Reference data for the clinic. Edit these lists to add doctors, services or branches.

The frontend loads them from GET /api/meta, so changes here show up on the booking form.
"""

DOCTORS = [
    {"slug": "feysel-alo", "name": "Dr. Feysel Alo"},
    {"slug": "zina-ahmed", "name": "Dr. Zina Ahmed"},
    {"slug": "elias-mulat", "name": "Dr. Elias Mulat"},
    {"slug": "hiwot-engida", "name": "Dr. Hiwot Engida"},
    {"slug": "dagmawit-mitku", "name": "Dr. Dagmawit Mitku"},
    {"slug": "meti-fekadu", "name": "Dr. Meti Fekadu"},
    {"slug": "solomon-worku", "name": "Dr. Solomon Worku"},
]

SERVICES = [
    {"slug": "general-dermatology", "name": "General Dermatology"},
    {"slug": "dermatologic-surgery", "name": "Dermatologic Surgery"},
    {"slug": "cosmetic-dermatology", "name": "Cosmetic Dermatology"},
    {"slug": "consultation", "name": "Consultation (not sure)"},
]

BRANCHES = [
    {"slug": "bole", "name": "Bole branch", "phone": "0920201929"},
    {"slug": "zenebework", "name": "Zenebework branch", "phone": "0919237070"},
]

APPOINTMENT_STATUSES = ["pending", "confirmed", "completed", "cancelled", "no_show"]
# Statuses that still hold a time slot
ACTIVE_STATUSES = ["pending", "confirmed"]


def _index(items):
    return {i["slug"]: i for i in items}


DOCTOR_BY_SLUG = _index(DOCTORS)
SERVICE_BY_SLUG = _index(SERVICES)
BRANCH_BY_SLUG = _index(BRANCHES)


def label(kind, slug):
    table = {"doctor": DOCTOR_BY_SLUG, "service": SERVICE_BY_SLUG, "branch": BRANCH_BY_SLUG}[kind]
    if not slug:
        return "Any available doctor" if kind == "doctor" else "-"
    return table.get(slug, {}).get("name", slug)
