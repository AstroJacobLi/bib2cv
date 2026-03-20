"""bib2cv — Convert BibTeX publications to LaTeX CV entries."""

__version__ = "0.1.0"

from .formatter import format_entries, format_entries_grouped  # noqa: F401
from .parser import parse_bibfile  # noqa: F401
