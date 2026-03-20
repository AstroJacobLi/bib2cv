"""Parse BibTeX files into structured entry dicts."""

from __future__ import annotations

import bibtexparser
from bibtexparser.bparser import BibTexParser


def parse_bibfile(path: str) -> list[dict]:
    """Parse a BibTeX file and return a list of entry dicts.

    Each dict contains the raw BibTeX fields with keys lowercased,
    plus ``"ID"`` for the citation key and ``"ENTRYTYPE"`` for the
    entry type (e.g. ``"article"``).

    Note: We intentionally do NOT apply ``convert_to_unicode`` so that
    raw LaTeX constructs (math, subscripts, braces) are preserved in
    titles and other fields.
    """
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False

    with open(path, encoding="utf-8") as f:
        bib_db = bibtexparser.load(f, parser=parser)

    return bib_db.entries


def parse_bibstring(bib_string: str) -> list[dict]:
    """Parse a BibTeX string and return a list of entry dicts.

    Convenience wrapper for testing and programmatic use.
    """
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False

    bib_db = bibtexparser.loads(bib_string, parser=parser)
    return bib_db.entries

