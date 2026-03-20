"""Format BibTeX entries into LaTeX CV \\item lines."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .journals import resolve_journal

# ---------------------------------------------------------------------------
# Month helpers
# ---------------------------------------------------------------------------

_MONTH_ORDER = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _month_num(raw: str | None) -> int:
    """Convert a BibTeX month value to an integer (1–12), or 0 if unknown."""
    if not raw:
        return 0
    raw_lower = raw.strip().lower().rstrip(".")
    if raw_lower in _MONTH_ORDER:
        return _MONTH_ORDER[raw_lower]
    # Some BibTeX files use numeric months
    try:
        return int(raw_lower)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class FormatterConfig:
    """Configuration for the CV formatter.

    Attributes:
        owner_last: Last name of the CV owner (for bolding).
        owner_first: First name(s) of the CV owner.
        max_position_before_truncation: If the owner's 1-indexed
            position in the author list is ≤ this, show all authors.
            Otherwise truncate.
        num_authors_when_truncated: Number of leading authors to show
            when the list is truncated (before ``et al.``).
        overrides: Per-entry overrides keyed by BibTeX citation key.
            Each value is a dict that may contain:
            - ``"status"``: one of ``"published"``, ``"accepted"``,
              ``"submitted"``, ``"in prep"``
            - ``"journal"``: override journal label
    """

    owner_last: str = "Li"
    owner_first: str = "Jiaxuan"
    max_position_before_truncation: int = 5
    num_authors_when_truncated: int = 4
    overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def load_overrides(cls, path: str, **kwargs) -> "FormatterConfig":
        """Create a config, loading per-entry overrides from a JSON file.

        The JSON file should be a dict mapping BibTeX keys to override
        dicts, e.g.::

            {
                "2025arXiv250408032M": {
                    "status": "accepted",
                    "journal": "ApJL"
                }
            }
        """
        with open(path, encoding="utf-8") as f:
            overrides = json.load(f)
        return cls(overrides=overrides, **kwargs)


# ---------------------------------------------------------------------------
# Author formatting
# ---------------------------------------------------------------------------


def _strip_braces(s: str) -> str:
    """Remove BibTeX protective braces from a string."""
    return s.replace("{", "").replace("}", "")


def _format_author_name(name: str) -> str:
    """Format a single author name from BibTeX ``Last, First M.`` style.

    Returns ``Last F.`` or ``Last F.~M.`` (with non-breaking space
    between initials for LaTeX).
    """
    # BibTeX author names are "Last, First [Middle ...]"
    parts = [p.strip() for p in name.split(",", maxsplit=1)]
    if len(parts) < 2:
        # No comma — single-token name (e.g. collaboration name)
        return name.strip()

    last = _strip_braces(parts[0].strip())
    firsts = _strip_braces(parts[1].strip()).split()

    if not firsts:
        return last

    # Build initials
    initials: list[str] = []
    for tok in firsts:
        # Already an initial like "E." or "J"
        if len(tok) <= 2 and tok.endswith("."):
            initials.append(tok)
        elif len(tok) == 1:
            initials.append(tok + ".")
        else:
            initials.append(tok[0] + ".")

    if len(initials) == 1:
        return f"{last} {initials[0]}"
    else:
        # Join with non-breaking space ~
        return f"{last} {'~'.join(initials)}"


def _is_owner(name: str, cfg: FormatterConfig) -> bool:
    """Check whether *name* (raw BibTeX form) matches the CV owner."""
    parts = [p.strip() for p in name.split(",", maxsplit=1)]
    if len(parts) < 2:
        return False
    last = _strip_braces(parts[0].strip())
    first_str = _strip_braces(parts[1].strip())
    first = first_str.split()[0] if first_str else ""
    return (
        last.lower() == cfg.owner_last.lower()
        and first.lower() == cfg.owner_first.lower()
    )


def _owner_formatted(cfg: FormatterConfig) -> str:
    """Return the bolded owner name string."""
    initials = [n[0] + "." for n in cfg.owner_first.split()]
    init_str = "~".join(initials) if len(initials) > 1 else initials[0]
    return rf"\textbf{{{cfg.owner_last} {init_str}}}"


def format_authors(author_field: str, cfg: FormatterConfig) -> str:
    """Format the author field into a CV-style author string.

    Handles bolding of the owner and truncation per config.
    """
    # Split on " and " (BibTeX convention)
    names = [n.strip() for n in author_field.split(" and ")]
    total = len(names)

    # Find owner position (1-indexed)
    owner_pos = None
    for i, name in enumerate(names):
        if _is_owner(name, cfg):
            owner_pos = i + 1
            break

    # Format each name
    formatted: list[str] = []
    for name in names:
        if _is_owner(name, cfg):
            formatted.append(_owner_formatted(cfg))
        else:
            formatted.append(_format_author_name(name))

    # Truncation logic
    if (
        owner_pos is not None
        and owner_pos > cfg.max_position_before_truncation
        and total > cfg.max_position_before_truncation
    ):
        n = cfg.num_authors_when_truncated
        truncated = formatted[:n]
        return ", ".join(truncated) + f" et al. (including {_owner_formatted(cfg)})"

    return ", ".join(formatted)


# ---------------------------------------------------------------------------
# Title formatting
# ---------------------------------------------------------------------------


def _get_link(entry: dict) -> str | None:
    """Return the best URL for the entry using link precedence."""
    # 1. ADS URL
    adsurl = entry.get("adsurl", "").strip()
    if adsurl:
        return adsurl

    # 2. DOI
    doi = entry.get("doi", "").strip()
    if doi:
        if doi.startswith("http"):
            return doi
        return f"https://doi.org/{doi}"

    # 3. arXiv
    eprint = entry.get("eprint", "").strip()
    if eprint:
        return f"https://arxiv.org/abs/{eprint}"

    return None


def _clean_title(title: str) -> str:
    """Clean a BibTeX title for LaTeX output.

    Strips outer braces added by BibTeX but preserves inner LaTeX
    (math, subscripts, etc.).
    """
    t = title.strip()
    # Remove outer braces if the entire title is wrapped
    if t.startswith("{") and t.endswith("}"):
        t = t[1:-1]
    return t


def format_title(entry: dict) -> str:
    """Format the title, wrapping in \\href if a link is available."""
    title = _clean_title(entry.get("title", ""))
    link = _get_link(entry)
    if link:
        return rf"\href{{{link}}}{{{title}}}"
    return title


# ---------------------------------------------------------------------------
# Journal / publication status
# ---------------------------------------------------------------------------


def _determine_status(entry: dict, cfg: FormatterConfig) -> str:
    """Determine publication status: published, accepted, submitted, arxiv, or in prep."""
    key = entry.get("ID", "")
    override = cfg.overrides.get(key, {})
    if "status" in override:
        return override["status"]

    journal_raw = entry.get("journal", "").strip()
    # "arXiv e-prints" is not a real journal
    is_arxiv_journal = journal_raw.lower() in ("arxiv e-prints", "arxiv")
    has_journal = bool(journal_raw) and not is_arxiv_journal

    # Heuristic: if there's a volume/pages/eid, it's published
    has_volume = bool(entry.get("volume", "").strip())
    has_pages = bool(
        entry.get("pages", "").strip() or entry.get("eid", "").strip()
    )

    if has_volume and has_pages and has_journal:
        return "published"

    if has_journal:
        # Has journal but no volume — likely accepted or submitted
        return "accepted"

    # arXiv only
    if entry.get("eprint", "").strip():
        return "arxiv"

    return "in prep"


def _get_journal_name(entry: dict, cfg: FormatterConfig) -> str:
    """Resolve the journal name, applying overrides if present."""
    key = entry.get("ID", "")
    override = cfg.overrides.get(key, {})
    if "journal" in override:
        return override["journal"]

    raw = entry.get("journal", "").strip()
    if not raw:
        return ""
    # "arXiv e-prints" is not a real journal name
    if raw.lower() in ("arxiv e-prints", "arxiv"):
        return ""
    return resolve_journal(raw)


def format_publication_info(entry: dict, cfg: FormatterConfig) -> str:
    """Format the journal/status portion of the CV entry.

    Returns strings like:
    - ``\\textit{ApJL} 998, L24 (2026).``
    - ``\\textit{ApJL} accepted.``
    - ``\\textit{ApJL} submitted.``
    - ``arXiv:2504.08032.``
    """
    status = _determine_status(entry, cfg)
    journal = _get_journal_name(entry, cfg)

    year = entry.get("year", "").strip()
    volume = entry.get("volume", "").strip()
    page = (entry.get("eid", "") or entry.get("pages", "")).strip()
    # Clean page of any range (just take first page)
    if "--" in page:
        page = page.split("--")[0]
    elif "-" in page:
        page = page.split("-")[0]

    eprint = entry.get("eprint", "").strip()

    if status == "published" and journal:
        return rf"\textit{{{journal}}} {volume}, {page} ({year})."

    if status == "accepted" and journal:
        if eprint:
            return rf"\textit{{{journal}}} accepted, arXiv:{eprint}."
        return rf"\textit{{{journal}}} accepted."

    if status == "submitted" and journal:
        if eprint:
            return rf"\textit{{{journal}}} submitted, arXiv:{eprint}."
        return rf"\textit{{{journal}}} submitted."

    if status == "arxiv":
        eprint = entry.get("eprint", "").strip()
        if journal:
            # arXiv paper with a known target journal (from override)
            return rf"\textit{{{journal}}} submitted, arXiv:{eprint}."
        return rf"arXiv:{eprint}."

    if status == "in prep":
        return "in prep."

    # Fallback
    if journal:
        return rf"\textit{{{journal}}}."
    return ""


# ---------------------------------------------------------------------------
# Entry assembly
# ---------------------------------------------------------------------------


def format_entry(
    entry: dict, cfg: FormatterConfig, *, skip_status: bool = False,
) -> str:
    """Format a single BibTeX entry as a LaTeX ``\\item`` line.

    If *skip_status* is True, the trailing publication-info is replaced
    by the ``"description"`` override (if set), or omitted entirely.
    """
    authors = format_authors(entry.get("author", ""), cfg)
    title = format_title(entry)

    if skip_status:
        key = entry.get("ID", "")
        desc = cfg.overrides.get(key, {}).get("description", "")
        eprint = entry.get("eprint", "").strip()
        if desc and eprint:
            return rf"\item {authors}, {title}, {desc}, arXiv:{eprint}."
        if desc:
            return rf"\item {authors}, {title}, {desc}."
        return rf"\item {authors}, {title}."

    pub_info = format_publication_info(entry, cfg)
    return rf"\item {authors}, {title}, {pub_info}"


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def _sort_key(entry: dict) -> tuple:
    """Sort key for reverse chronological ordering.

    Returns (neg_year, neg_month, title) so that ``sorted()``
    gives newest-first, with alphabetical title as tiebreaker.
    """
    try:
        year = int(entry.get("year", "0"))
    except ValueError:
        year = 0
    month = _month_num(entry.get("month"))
    title = entry.get("title", "").lower()
    return (-year, -month, title)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def format_entries(
    entries: list[dict],
    cfg: FormatterConfig | None = None,
    sort: bool = True,
) -> str:
    """Format a list of BibTeX entries into LaTeX ``\\item`` lines.

    Parameters
    ----------
    entries : list[dict]
        Entries as returned by :func:`bib2cv.parser.parse_bibfile`.
    cfg : FormatterConfig, optional
        Formatting configuration. Uses defaults if not provided.
    sort : bool
        Whether to sort entries reverse-chronologically (default True).

    Returns
    -------
    str
        Newline-separated ``\\item`` lines ready for a LaTeX
        ``itemize`` or ``enumerate`` environment.
    """
    if cfg is None:
        cfg = FormatterConfig()

    if sort:
        entries = sorted(entries, key=_sort_key)

    lines = [format_entry(e, cfg) for e in entries]
    return "\n\n".join(lines)


def _owner_position(entry: dict, cfg: FormatterConfig) -> int | None:
    """Return the 1-indexed position of the owner in the author list, or None."""
    author_field = entry.get("author", "")
    names = [n.strip() for n in author_field.split(" and ")]
    for i, name in enumerate(names):
        if _is_owner(name, cfg):
            return i + 1
    return None


# Patterns in BibTeX keys that indicate misc entries (case-insensitive)
_MISC_KEY_PATTERNS = (
    "AAS",       # AAS meeting abstracts
    "prop",      # telescope proposals (HST, JWST, Roman, etc.)
    "mla..conf", # ML for Astrophysics conference
    "conf",      # other conferences
    "ngr..prop", # NASA proposals
    "mpec",      # Minor Planet Electronic Circulars
    "zndo",      # Zenodo software releases
)

# Entry types that are always misc
_MISC_ENTRY_TYPES = {"misc", "inproceedings", "software"}


def _is_misc_entry(entry: dict) -> bool:
    """Check if a BibTeX entry is a misc item (abstract, proposal, conference).

    Detection uses both:
    - BibTeX entry type (``MISC``, ``INPROCEEDINGS``)
    - Key patterns matching ADS conventions (e.g. ``AAS``, ``prop``,
      ``conf`` in the BibTeX key)
    """
    entry_type = entry.get("ENTRYTYPE", "").lower()
    if entry_type in _MISC_ENTRY_TYPES:
        return True

    key = entry.get("ID", "")
    for pattern in _MISC_KEY_PATTERNS:
        if pattern.lower() in key.lower():
            return True

    return False


def format_entries_grouped(
    entries: list[dict],
    cfg: FormatterConfig | None = None,
    section_headers: dict[str, str] | None = None,
) -> str:
    """Format entries grouped by the owner's author position.

    Groups (in order):
    - **First-author**: owner is 1st author
    - **Second/third-author**: owner is 2nd or 3rd author
    - **Nth-author**: owner is 4th+ or not found
    - **Misc**: AAS abstracts, proposals, conference proceedings

    Each group is sorted reverse-chronologically.

    Parameters
    ----------
    entries : list[dict]
        Entries as returned by :func:`bib2cv.parser.parse_bibfile`.
    cfg : FormatterConfig, optional
        Formatting configuration.
    section_headers : dict, optional
        Override group headers. Keys: ``"first"``, ``"second_third"``,
        ``"nth"``, ``"misc"``. Defaults to descriptive LaTeX comments.

    Returns
    -------
    str
        Grouped, formatted entries with section headers.
    """
    if cfg is None:
        cfg = FormatterConfig()

    if section_headers is None:
        section_headers = {
            "first": "% ---- First-author papers ----",
            "second_third": "% ---- Second/third-author papers ----",
            "nth": "% ---- Other papers ----",
            "misc": "% ---- Misc (abstracts, proposals, proceedings) ----",
        }

    first: list[dict] = []
    second_third: list[dict] = []
    nth: list[dict] = []
    misc: list[dict] = []

    for entry in entries:
        key = entry.get("ID", "")
        entry_overrides = cfg.overrides.get(key, {})

        # Skip entries explicitly marked to skip
        if entry_overrides.get("skip"):
            continue

        has_desc_override = "description" in entry_overrides
        if _is_misc_entry(entry) or has_desc_override:
            misc.append(entry)
            continue

        pos = _owner_position(entry, cfg)
        if pos == 1:
            first.append(entry)
        elif pos is not None and pos <= 3:
            second_third.append(entry)
        else:
            nth.append(entry)

    # Sort each group reverse-chronologically
    for group in (first, second_third, nth, misc):
        group.sort(key=_sort_key)

    sections: list[str] = []
    for header_key, group in [
        ("first", first),
        ("second_third", second_third),
        ("nth", nth),
        ("misc", misc),
    ]:
        if group:
            header = section_headers.get(header_key, "")
            is_misc = header_key == "misc"
            lines = [
                format_entry(e, cfg, skip_status=is_misc) for e in group
            ]
            section = header + "\n\n" + "\n\n".join(lines) if header else "\n\n".join(lines)
            sections.append(section)

    return "\n\n".join(sections)


