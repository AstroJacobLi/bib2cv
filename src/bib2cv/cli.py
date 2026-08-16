"""Command-line interface for bib2cv."""

from __future__ import annotations

import argparse
import sys

from .formatter import (
    LATEX_PREAMBLE,
    FormatterConfig,
    format_entries,
    format_entries_grouped,
)
from .parser import parse_bibfile


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``bib2cv`` CLI."""
    parser = argparse.ArgumentParser(
        prog="bib2cv",
        description="Convert BibTeX publications to LaTeX CV entries.",
    )
    parser.add_argument(
        "bibfile",
        help="Path to the BibTeX file.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output file (default: stdout).",
    )
    parser.add_argument(
        "--author",
        default="Li, Jiaxuan",
        help=(
            "Full name of the CV owner as 'Last, First' "
            "(default: 'Li, Jiaxuan')."
        ),
    )
    parser.add_argument(
        "--overrides",
        default=None,
        help="Path to JSON file with per-entry overrides.",
    )
    parser.add_argument(
        "--max-position",
        type=int,
        default=5,
        help=(
            "If the owner's position exceeds this, truncate the "
            "author list (default: 5)."
        ),
    )
    parser.add_argument(
        "--max-authors",
        type=int,
        default=None,
        help=(
            "Cap the number of authors shown per entry; longer lists "
            "are truncated to this many names followed by 'et al.' "
            "(default: no cap)."
        ),
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        help="Disable reverse-chronological sorting.",
    )
    parser.add_argument(
        "--preamble",
        action="store_true",
        help=(
            "Prepend a LaTeX package/colour preamble block (hyperref, "
            "fontenc, a U+2500 dash fix, link colours, etc.). Meant to "
            "be \\input into your CV's preamble; does not compile alone."
        ),
    )
    parser.add_argument(
        "--no-group",
        action="store_true",
        help=(
            "Disable grouping by author position. "
            "By default, papers are grouped into first-author, "
            "2nd/3rd-author, and other."
        ),
    )

    args = parser.parse_args(argv)

    # Parse author name
    author_parts = [p.strip() for p in args.author.split(",", maxsplit=1)]
    if len(author_parts) != 2:
        parser.error("--author must be in 'Last, First' format.")
    owner_last, owner_first = author_parts

    # Build config
    if args.overrides:
        cfg = FormatterConfig.load_overrides(
            args.overrides,
            owner_last=owner_last,
            owner_first=owner_first,
            max_position_before_truncation=args.max_position,
            max_authors=args.max_authors,
        )
    else:
        cfg = FormatterConfig(
            owner_last=owner_last,
            owner_first=owner_first,
            max_position_before_truncation=args.max_position,
            max_authors=args.max_authors,
        )

    # Parse and format
    entries = parse_bibfile(args.bibfile)
    if args.no_group:
        output = format_entries(entries, cfg=cfg, sort=not args.no_sort)
    else:
        output = format_entries_grouped(entries, cfg=cfg)

    if args.preamble:
        output = LATEX_PREAMBLE + "\n\n" + output

    # Write
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print(f"Wrote {len(entries)} entries to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
