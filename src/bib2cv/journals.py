"""Mapping of ADS BibTeX journal macros to CV-style short names."""

# Keys are the BibTeX macro string (without backslash prefix in some cases,
# but we store both forms for robust matching).
# Values are the short CV-style journal names.

JOURNAL_MAP: dict[str, str] = {
    # --- Astrophysical Journal family ---
    r"\apj": "ApJ",
    r"\apjl": "ApJL",
    r"\apjlett": "ApJL",
    r"\apjs": "ApJS",
    r"\apjsupp": "ApJS",
    # --- Astronomical Journal ---
    r"\aj": "AJ",
    # --- MNRAS ---
    r"\mnras": "MNRAS",
    # --- Astronomy & Astrophysics ---
    r"\aap": "A\\&A",
    r"\aa": "A\\&A",
    # --- Annual Reviews ---
    r"\araa": "ARA\\&A",
    # --- PASP ---
    r"\pasp": "PASP",
    # --- Nature family ---
    r"\nat": "Nature",
    r"\nature": "Nature",
    r"\natas": "Nat. Astron.",
    r"\na": "Nat. Astron.",
    # --- Science ---
    r"\sci": "Science",
    r"\science": "Science",
    # --- Physical Review ---
    r"\prd": "Phys. Rev. D",
    r"\prl": "Phys. Rev. Lett.",
    # --- Other ---
    r"\icarus": "Icarus",
    r"\planss": "Planet. Space Sci.",
    r"\ssr": "Space Sci. Rev.",
    r"\baas": "BAAS",
    r"\jcap": "JCAP",
    r"\aaps": "A\\&AS",
    r"\pasj": "PASJ",
    r"\aapr": "A\\&A Rev.",
    r"\solphys": "Sol. Phys.",
    r"\gca": "Geochim. Cosmochim. Acta",
    r"\memras": "Mem. RAS",
    # --- Research Notes ---
    r"\rnaas": "RNAAS",
}

# Also support plain-text full journal names → abbreviation
_FULLNAME_MAP: dict[str, str] = {
    "The Astrophysical Journal": "ApJ",
    "The Astrophysical Journal Letters": "ApJL",
    "The Astrophysical Journal Supplement Series": "ApJS",
    "The Astronomical Journal": "AJ",
    "Monthly Notices of the Royal Astronomical Society": "MNRAS",
    "Astronomy and Astrophysics": "A\\&A",
    "Astronomy & Astrophysics": "A\\&A",
    "Annual Review of Astronomy and Astrophysics": "ARA\\&A",
    "Publications of the Astronomical Society of the Pacific": "PASP",
    "Nature": "Nature",
    "Nature Astronomy": "Nat. Astron.",
    "Science": "Science",
    "Physical Review D": "Phys. Rev. D",
    "Physical Review Letters": "Phys. Rev. Lett.",
    "Research Notes of the AAS": "RNAAS",
    "Research Notes of the American Astronomical Society": "RNAAS",
}


def resolve_journal(raw: str) -> str:
    """Resolve a BibTeX journal field to a CV-style short name.

    Tries, in order:
    1. Exact match against ADS macros (e.g., ``\\apjl``).
    2. Exact match against full journal names.
    3. Return the raw string unchanged (already a usable name).
    """
    raw_stripped = raw.strip()

    # 1. ADS macro match
    if raw_stripped in JOURNAL_MAP:
        return JOURNAL_MAP[raw_stripped]

    # 2. Full-name match
    if raw_stripped in _FULLNAME_MAP:
        return _FULLNAME_MAP[raw_stripped]

    # 3. Pass through
    return raw_stripped
