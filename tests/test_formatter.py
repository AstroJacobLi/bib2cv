"""Tests for bib2cv.formatter — author, title, journal, and entry formatting."""

from __future__ import annotations

import pytest

from bib2cv.formatter import (
    FormatterConfig,
    _format_author_name,
    _is_owner,
    _owner_formatted,
    format_authors,
    format_entry,
    format_publication_info,
    format_title,
    format_entries,
)


# ===================================================================
# Author name formatting
# ===================================================================


class TestFormatAuthorName:
    def test_single_first(self):
        assert _format_author_name("Li, Jiaxuan") == "Li J."

    def test_two_names(self):
        assert _format_author_name("Greene, Jenny E.") == "Greene J.~E."

    def test_two_names_full(self):
        assert _format_author_name("Carlsten, Scott G.") == "Carlsten S.~G."

    def test_single_token(self):
        # Collaboration names, etc.
        assert _format_author_name("SDSS Collaboration") == "SDSS Collaboration"


# ===================================================================
# Owner detection
# ===================================================================


class TestOwnerDetection:
    def setup_method(self):
        self.cfg = FormatterConfig()

    def test_matches(self):
        assert _is_owner("Li, Jiaxuan", self.cfg) is True

    def test_no_match_different_last(self):
        assert _is_owner("Greene, Jenny E.", self.cfg) is False

    def test_no_match_different_first(self):
        assert _is_owner("Li, Someone", self.cfg) is False

    def test_owner_formatted(self):
        assert _owner_formatted(self.cfg) == r"\textbf{Li J.}"


# ===================================================================
# Author list formatting (truncation)
# ===================================================================


class TestFormatAuthors:
    def setup_method(self):
        self.cfg = FormatterConfig()

    def test_first_author(self):
        authors = "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany"
        result = format_authors(authors, self.cfg)
        assert result.startswith(r"\textbf{Li J.}")
        assert "Greene J.~E." in result
        assert "Danieli S." in result

    def test_second_author(self):
        authors = "Cheng, Sihao and Li, Jiaxuan and Yang, Erhai"
        result = format_authors(authors, self.cfg)
        assert r"\textbf{Li J.}" in result
        assert result.startswith("Cheng S.")

    def test_truncation_beyond_5(self):
        """Owner at position 9 → show first 4 + et al."""
        authors = (
            "Ma, Yilun and Greene, Jenny E. and Setton, David J. and "
            "Goulding, Andy D. and Annunziatella, Marianna and "
            "Fan, Xiaohui and Kokorev, Vasily and Labbe, Ivo and "
            "Li, Jiaxuan and Lin, Xiaojing"
        )
        result = format_authors(authors, self.cfg)
        assert result.startswith("Ma Y.")
        assert "et al." in result
        assert r"including \textbf{Li J.}" in result
        # Should only show first 4 names
        assert "Annunziatella" not in result

    def test_no_truncation_at_position_5(self):
        """Owner at position 5 → full list."""
        authors = (
            "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany and "
            "Carlsten, Scott G. and Geha, Marla"
        )
        result = format_authors(authors, self.cfg)
        assert "et al." not in result
        assert "Geha M." in result


# ===================================================================
# Title formatting
# ===================================================================


class TestFormatTitle:
    def test_href_with_adsurl(self):
        entry = {
            "title": "{A Possible Paper Title}",
            "adsurl": "https://ui.adsabs.harvard.edu/abs/2026test",
            "doi": "10.1234/test",
        }
        result = format_title(entry)
        assert r"\href{https://ui.adsabs.harvard.edu/abs/2026test}" in result
        assert "A Possible Paper Title" in result

    def test_href_doi_fallback(self):
        entry = {
            "title": "{Test Title}",
            "doi": "10.1234/test",
        }
        result = format_title(entry)
        assert r"\href{https://doi.org/10.1234/test}" in result

    def test_href_arxiv_fallback(self):
        entry = {
            "title": "{Test Title}",
            "eprint": "2501.00001",
        }
        result = format_title(entry)
        assert r"\href{https://arxiv.org/abs/2501.00001}" in result

    def test_no_link(self):
        entry = {"title": "{Test Title}"}
        result = format_title(entry)
        assert result == "Test Title"
        assert r"\href" not in result

    def test_preserves_math(self):
        entry = {
            "title": "{Counting Little Red Dots at z < 4}",
            "adsurl": "https://example.com",
        }
        result = format_title(entry)
        assert "z < 4" in result

    def test_preserves_subscripts(self):
        entry = {
            "title": r"{2017 OF$_{201}$}",
            "adsurl": "https://example.com",
        }
        result = format_title(entry)
        assert r"OF$_{201}$" in result


# ===================================================================
# Publication info
# ===================================================================


class TestPublicationInfo:
    def setup_method(self):
        self.cfg = FormatterConfig()

    def test_published(self):
        entry = {
            "ID": "test",
            "journal": r"\apjl",
            "volume": "998",
            "eid": "L24",
            "year": "2026",
        }
        result = format_publication_info(entry, self.cfg)
        assert result == r"\textit{ApJL} 998, L24 (2026)."

    def test_accepted(self):
        entry = {
            "ID": "test",
            "journal": r"\apjl",
            "year": "2025",
        }
        result = format_publication_info(entry, self.cfg)
        assert result == r"\textit{ApJL} accepted."

    def test_accepted_override(self):
        cfg = FormatterConfig(overrides={"test": {"status": "accepted", "journal": "ApJL"}})
        entry = {
            "ID": "test",
            "journal": r"\apj",
            "volume": "100",
            "eid": "1",
            "year": "2025",
        }
        result = format_publication_info(entry, cfg)
        assert result == r"\textit{ApJL} accepted."

    def test_arxiv_only(self):
        entry = {
            "ID": "test",
            "eprint": "2501.00001",
            "year": "2025",
        }
        result = format_publication_info(entry, self.cfg)
        assert result == "arXiv:2501.00001."

    def test_arxiv_with_journal_override(self):
        cfg = FormatterConfig(overrides={"test": {"journal": "ApJL"}})
        entry = {
            "ID": "test",
            "eprint": "2501.00001",
            "year": "2025",
        }
        result = format_publication_info(entry, cfg)
        assert result == r"\textit{ApJL} submitted, arXiv:2501.00001."


# ===================================================================
# Full entry
# ===================================================================


class TestFormatEntry:
    def test_full_entry(self):
        cfg = FormatterConfig()
        entry = {
            "ID": "2026ApJ...998L..24L",
            "author": "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany and Carlsten, Scott G. and Geha, Marla",
            "title": "{A Possible ``Too-Many-Satellites'' Problem in the Isolated Dwarf Galaxy DDO~161}",
            "journal": r"\apjl",
            "year": "2026",
            "month": "jan",
            "volume": "998",
            "eid": "L24",
            "adsurl": "https://ui.adsabs.harvard.edu/abs/2026ApJ...998L..24L",
        }
        result = format_entry(entry, cfg)
        assert result.startswith(r"\item \textbf{Li J.}")
        assert r"\href{https://ui.adsabs.harvard.edu/abs/2026ApJ...998L..24L}" in result
        assert r"\textit{ApJL} 998, L24 (2026)." in result


# ===================================================================
# Sorting
# ===================================================================


class TestSorting:
    def test_reverse_chronological(self):
        cfg = FormatterConfig()
        entries = [
            {"author": "Li, Jiaxuan", "title": "B", "year": "2024", "month": "jan"},
            {"author": "Li, Jiaxuan", "title": "A", "year": "2026", "month": "mar"},
            {"author": "Li, Jiaxuan", "title": "C", "year": "2026", "month": "jan"},
        ]
        output = format_entries(entries, cfg)
        lines = [l for l in output.split("\n") if l.strip()]
        # 2026/mar first, then 2026/jan, then 2024/jan
        assert "A" in lines[0]
        assert "C" in lines[1]
        assert "B" in lines[2]
