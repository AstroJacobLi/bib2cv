"""Format BibTeX entries into LaTeX CV \\item lines."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .journals import resolve_journal

# ---------------------------------------------------------------------------
# LaTeX preamble
# ---------------------------------------------------------------------------

# Package/colour block that can optionally be prepended to the output
# (via the ``--preamble`` CLI flag). These are preamble-only commands, so
# the result is meant to be ``\input`` into the preamble of your own CV
# document, not compiled on its own. ``\DeclareUnicodeCharacter{2500}{---}``
# guards against the U+2500 box-drawing dash that ADS sometimes emits in
# titles (e.g. "SN 2022oqm─A Ca-rich ...").
LATEX_PREAMBLE = r"""\usepackage{hyperref}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{enumitem}
\usepackage[utf8]{inputenc}
\DeclareUnicodeCharacter{2500}{---}
\RequirePackage{color,graphicx}
\usepackage[usenames,dvipsnames]{xcolor}
%Setup hyperref package, and colours for links
\usepackage{hyperref}
\definecolor{linkcolour}{rgb}{0,0.2,0.6}
\hypersetup{colorlinks,breaklinks,urlcolor=linkcolour, linkcolor=linkcolour}"""


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
        max_authors: Hard cap on the number of authors displayed for a
            single entry. When a list is longer than this, only the
            leading ``max_authors`` names are shown, followed by
            ``et al.`` (used mainly to shorten long first-author lists).
            ``None`` disables the cap.
        overrides: Per-entry overrides keyed by BibTeX citation key.
            Each value is a dict that may contain:
            - ``"status"``: one of ``"published"``, ``"accepted"``,
              ``"submitted"``, ``"in prep"``
            - ``"journal"``: override journal label
            - ``"co_first"``: mark equal-contribution authorship —
              ``true`` daggers the owner, an integer ``N`` daggers the
              leading ``N`` authors; either promotes the paper to the
              first-author group.
    """

    owner_last: str = "Li"
    owner_first: str = "Jiaxuan"
    max_position_before_truncation: int = 5
    num_authors_when_truncated: int = 4
    max_authors: Optional[int] = None
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

# Superscript symbol appended to co-first (equal-contribution) authors.
# Add a matching footnote to your CV once, e.g.
# ``$^{\dagger}$ denotes equal contribution``.
CO_FIRST_MARKER = r"$^{\dagger}$"


def _co_first_positions(
    co_first, owner_pos: int | None, total: int
) -> set[int]:
    """Resolve which 1-indexed author positions are co-first authors.

    *co_first* comes from the per-entry ``"co_first"`` override:
    - ``True`` → mark only the owner (if present in the list).
    - an integer ``N`` → mark the leading ``N`` authors (the common
      "first N share equal contribution" case).
    - falsy / ``None`` → mark nothing.
    """
    if not co_first:
        return set()
    if co_first is True:
        return {owner_pos} if owner_pos is not None else set()
    try:
        n = int(co_first)
    except (TypeError, ValueError):
        return set()
    return set(range(1, min(n, total) + 1))


def _strip_braces(s: str) -> str:
    """Remove BibTeX protective braces while preserving LaTeX accents.

    Braces that merely protect capitalization (e.g. ``{Chen}``) are
    removed, but a brace group beginning with a backslash command
    (e.g. ``{\\k{a}}`` → ą, ``{\\.z}`` → ż, ``{\\"u}`` → ü) is kept
    intact — stripping its braces would turn ``\\k{a}`` into the
    undefined control word ``\\ka`` and break compilation.
    """
    result: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "{":
            # Find the matching closing brace for this group.
            depth, j = 1, i + 1
            while j < n and depth:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < n:  # balanced group s[i..j]
                content = s[i + 1:j]
                if content.startswith("\\"):
                    # LaTeX command/accent group — keep verbatim.
                    result.append(s[i:j + 1])
                else:
                    # Protective braces — drop them, recurse into content.
                    result.append(_strip_braces(content))
                i = j + 1
            else:  # unbalanced; leave as-is
                result.append(c)
                i += 1
        elif c == "}":
            i += 1  # stray closing brace
        else:
            result.append(c)
            i += 1
    return "".join(result)


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


def _first_name_matches(entry_first: str, owner_first: str) -> bool:
    """Compare two given-name tokens, letting an initial match a full name.

    ADS BibTeX is inconsistent — the same person may appear as ``Ping``
    in one entry and ``P.`` in another. So ``"P."`` matches ``"Ping"``
    (and vice versa). When *both* names are spelled out, they must match
    exactly (case-insensitive), so ``"Peter"`` does not match ``"Ping"``.
    """
    e = entry_first.rstrip(".").lower()
    o = owner_first.rstrip(".").lower()
    if not e or not o:
        return False
    # Both spelled out → require a full match.
    if len(e) > 1 and len(o) > 1:
        return e == o
    # At least one is an initial → compare the leading letter only.
    return e[0] == o[0]


def _is_owner(name: str, cfg: FormatterConfig) -> bool:
    """Check whether *name* (raw BibTeX form) matches the CV owner.

    Matches on last name plus the first given name, tolerating the
    initial-vs-spelled-out mismatch common in ADS exports (e.g. both
    ``Chen, Ping`` and ``Chen, P.`` match owner ``Chen, Ping``).
    """
    parts = [p.strip() for p in name.split(",", maxsplit=1)]
    if len(parts) < 2:
        return False
    last = _strip_braces(parts[0].strip())
    first_str = _strip_braces(parts[1].strip())
    first = first_str.split()[0] if first_str else ""
    owner_first = cfg.owner_first.split()[0] if cfg.owner_first.split() else ""
    return (
        last.lower() == cfg.owner_last.lower()
        and _first_name_matches(first, owner_first)
    )


def _owner_formatted(cfg: FormatterConfig) -> str:
    """Return the bolded owner name string."""
    initials = [n[0] + "." for n in cfg.owner_first.split()]
    init_str = "~".join(initials) if len(initials) > 1 else initials[0]
    return rf"\textbf{{{cfg.owner_last} {init_str}}}"


def format_authors(
    author_field: str, cfg: FormatterConfig, co_first=None
) -> str:
    """Format the author field into a CV-style author string.

    Handles bolding of the owner and truncation per config. *co_first*
    (from the per-entry ``"co_first"`` override) marks equal-contribution
    authors with a superscript dagger: ``True`` marks the owner, an
    integer ``N`` marks the leading ``N`` authors.
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

    mark_positions = _co_first_positions(co_first, owner_pos, total)

    # Format each name
    formatted: list[str] = []
    for i, name in enumerate(names):
        if _is_owner(name, cfg):
            rendered = _owner_formatted(cfg)
        else:
            rendered = _format_author_name(name)
        if (i + 1) in mark_positions:
            rendered += CO_FIRST_MARKER
        formatted.append(rendered)

    # Truncation logic
    #
    # Case 1: the owner is a minor author, appearing late in the list.
    # Show a few leading authors and note that the owner is included.
    if (
        owner_pos is not None
        and owner_pos > cfg.max_position_before_truncation
        and total > cfg.max_position_before_truncation
    ):
        # Show up to the display cap (``max_authors``) when it is set,
        # otherwise the default leading count. Honouring the cap here keeps
        # the owner — and any co-authors up to the cap — visible when the
        # owner sits just past ``max_position`` but within the cap.
        n = (
            cfg.max_authors
            if cfg.max_authors is not None
            else cfg.num_authors_when_truncated
        )
        if total <= n:
            # Everything fits within the cap; nothing to truncate.
            return ", ".join(formatted)
        truncated = formatted[:n]
        # If the owner already appears within the shown slice, don't also
        # append "(including ...)" — that would list them twice.
        if owner_pos <= n:
            return ", ".join(truncated) + " et al."
        return ", ".join(truncated) + f" et al. (including {_owner_formatted(cfg)})"

    # Case 2: the owner is a prominent author (e.g. first author) but the
    # list is long. Cap the number of displayed authors and append
    # ``et al.``. If the owner would fall past the cap, keep them visible.
    if cfg.max_authors is not None and total > cfg.max_authors:
        shown = formatted[: cfg.max_authors]
        if owner_pos is not None and owner_pos > cfg.max_authors:
            return ", ".join(shown) + f" et al. (including {_owner_formatted(cfg)})"
        return ", ".join(shown) + " et al."

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


def format_title(entry: dict, cfg: FormatterConfig | None = None) -> str:
    """Format the title, wrapping in \\href if a link is available.

    If a ``"title"`` override exists in *cfg*, it is used instead of
    the BibTeX title (useful for software entries, etc.).
    """
    if cfg is not None:
        key = entry.get("ID", "")
        title_override = cfg.overrides.get(key, {}).get("title")
        if title_override:
            title = title_override
        else:
            title = _clean_title(entry.get("title", ""))
    else:
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
    key = entry.get("ID", "")
    co_first = cfg.overrides.get(key, {}).get("co_first")
    authors = format_authors(entry.get("author", ""), cfg, co_first=co_first)
    title = format_title(entry, cfg)

    if skip_status:
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


# Substring patterns in BibTeX keys that indicate misc entries
# (case-insensitive).
_MISC_KEY_PATTERNS = (
    "prop",      # telescope proposals (HST, JWST, Roman, etc.)
    "mla..conf", # ML for Astrophysics conference
    "conf",      # other conferences
    "ngr..prop", # NASA proposals
    "mpec",      # Minor Planet Electronic Circulars
    "zndo",      # Zenodo software releases
)

# AAS meeting abstracts have bibcodes like ``2024AAS...24326110L`` — the
# journal field ``AAS`` sits right after the 4-digit year. Anchoring here
# avoids matching real journals whose code merely *contains* "AAS", most
# notably RNAAS (Research Notes of the AAS), e.g. ``2017RNAAS...1...28P``.
_AAS_ABSTRACT_KEY = re.compile(r"^\d{4}AAS", re.IGNORECASE)

# Entry types that are always misc
_MISC_ENTRY_TYPES = {"misc", "inproceedings", "software"}


def _is_misc_entry(entry: dict) -> bool:
    """Check if a BibTeX entry is a misc item (abstract, proposal, conference).

    Detection uses both:
    - BibTeX entry type (``MISC``, ``INPROCEEDINGS``)
    - Key patterns matching ADS conventions (e.g. AAS meeting abstracts,
      ``prop``, ``conf`` in the BibTeX key)
    """
    entry_type = entry.get("ENTRYTYPE", "").lower()
    if entry_type in _MISC_ENTRY_TYPES:
        return True

    key = entry.get("ID", "")
    if _AAS_ABSTRACT_KEY.match(key):
        return True
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
        # A co-first author paper counts as first-author, even if the
        # owner is listed 2nd/3rd.
        if pos == 1 or entry_overrides.get("co_first"):
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


