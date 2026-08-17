"""Tests for bib2cv.formatter — author, title, journal, and entry formatting."""

from __future__ import annotations

import pytest

from bib2cv.formatter import (
    CO_FIRST_MARKER,
    FormatterConfig,
    _format_author_name,
    _is_misc_entry,
    _is_owner,
    _owner_formatted,
    _strip_braces,
    format_authors,
    format_entry,
    format_entries_grouped,
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

    def test_preserves_letter_accent_macros(self):
        """Braces around \\k{a}, \\.z etc. must survive so LaTeX compiles."""
        # Drążkowska: \k{a} (ogonek) and \.z (dot). Stripping braces would
        # yield the undefined control word \ka.
        result = _format_author_name(r"{Dr{\k{a}}{\.z}kowska}, Joanna")
        assert result == r"Dr{\k{a}}{\.z}kowska J."
        assert r"\ka" not in result

    def test_preserves_symbol_accents(self):
        assert _format_author_name(r"{M{\"u}ller-Bravo}, Tom{\'a}s E.") == (
            r"M{\"u}ller-Bravo T.~E."
        )

    def test_strips_protective_braces(self):
        assert _strip_braces("{Chen}") == "Chen"
        assert _strip_braces("{Gal-Yam}") == "Gal-Yam"


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

    def test_matches_initial_form(self):
        """Owner spelled out in config, initial in the entry (ADS variance)."""
        assert _is_owner("Li, J.", self.cfg) is True

    def test_matches_when_owner_given_as_initial(self):
        """Symmetric: owner configured as an initial, entry spelled out."""
        cfg = FormatterConfig(owner_last="Li", owner_first="J.")
        assert _is_owner("Li, Jiaxuan", cfg) is True

    def test_initial_does_not_match_different_letter(self):
        assert _is_owner("Li, K.", self.cfg) is False

    def test_two_full_names_must_match_exactly(self):
        """An initial may match a full name, but two full names may not differ."""
        assert _is_owner("Li, Jason", self.cfg) is False

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

    def test_no_double_owner_when_shown_in_slice(self):
        """Owner past max_position but within the shown slice → no double listing."""
        # max_position=3, owner at position 4, num_authors_when_truncated=4.
        # The owner is the 4th shown name, so "(including ...)" must NOT
        # be appended.
        cfg = FormatterConfig(max_position_before_truncation=3)
        authors = (
            "Hinkle, John T. and Liu, Chang and Miller, Adam A. and "
            "Li, Jiaxuan and Payne, Alexander and Auchettl, Katie"
        )
        result = format_authors(authors, cfg)
        assert result.count(r"\textbf{Li J.}") == 1
        assert "including" not in result
        assert result.endswith(" et al.")

    def test_no_truncation_at_position_5(self):
        """Owner at position 5 → full list."""
        authors = (
            "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany and "
            "Carlsten, Scott G. and Geha, Marla"
        )
        result = format_authors(authors, self.cfg)
        assert "et al." not in result
        assert "Geha M." in result

    def test_max_authors_first_author(self):
        """First author + long list → first N names, plain 'et al.'."""
        cfg = FormatterConfig(max_authors=5)
        authors = (
            "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany and "
            "Carlsten, Scott G. and Geha, Marla and Kado-Fong, Erin and "
            "Goulding, Andy D."
        )
        result = format_authors(authors, cfg)
        assert result.startswith(r"\textbf{Li J.}")
        assert result.endswith(" et al.")
        # Plain 'et al.'—owner is already shown, so no '(including ...)'.
        assert "including" not in result
        assert "Geha M." in result  # 5th author is within the cap
        assert "Kado-Fong" not in result  # 6th author is dropped

    def test_max_authors_no_truncation_when_short(self):
        """List no longer than the cap → untouched."""
        cfg = FormatterConfig(max_authors=5)
        authors = "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany"
        result = format_authors(authors, cfg)
        assert "et al." not in result
        assert "Danieli S." in result

    def test_max_authors_keeps_owner_visible(self):
        """Owner past the cap but not 'late' → still noted via 'including'."""
        cfg = FormatterConfig(max_authors=3, max_position_before_truncation=10)
        authors = (
            "Greene, Jenny E. and Danieli, Shany and Carlsten, Scott G. and "
            "Geha, Marla and Li, Jiaxuan"
        )
        result = format_authors(authors, cfg)
        assert result.endswith(f" et al. (including {_owner_formatted(cfg)})")
        assert "Geha M." not in result  # beyond the cap

    def test_max_authors_none_shows_all(self):
        """Default (no cap) leaves long first-author lists intact."""
        cfg = FormatterConfig()  # max_authors defaults to None
        authors = (
            "Li, Jiaxuan and Greene, Jenny E. and Danieli, Shany and "
            "Carlsten, Scott G. and Geha, Marla and Kado-Fong, Erin"
        )
        result = format_authors(authors, cfg)
        assert "et al." not in result
        assert "Kado-Fong E." in result


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


# ===================================================================
# Misc-entry classification
# ===================================================================


class TestMiscClassification:
    def test_aas_meeting_abstract_is_misc(self):
        """AAS abstract bibcodes (AAS right after the year) are misc."""
        assert _is_misc_entry({"ID": "2024AAS...24326110L"}) is True

    def test_rnaas_is_not_misc(self):
        """RNAAS is a real journal, not an AAS meeting abstract."""
        assert _is_misc_entry({"ID": "2017RNAAS...1...28P"}) is False

    def test_proposal_is_misc(self):
        assert _is_misc_entry({"ID": "2025hst..prop18046L"}) is True

    def test_regular_article_is_not_misc(self):
        assert _is_misc_entry({"ID": "2024Natur.625..253C"}) is False

    def test_misc_entry_type_is_misc(self):
        assert _is_misc_entry({"ID": "whatever", "ENTRYTYPE": "software"}) is True


# ===================================================================
# Co-first authorship
# ===================================================================


class TestCoFirstAuthor:
    def setup_method(self):
        self.cfg = FormatterConfig()

    def test_true_marks_owner_only(self):
        """co_first=True daggers the owner and no one else."""
        authors = "Irani, Ido and Li, Jiaxuan and Morag, Jonathan"
        result = format_authors(authors, self.cfg, co_first=True)
        assert r"\textbf{Li J.}" + CO_FIRST_MARKER in result
        assert "Irani I." + CO_FIRST_MARKER not in result

    def test_true_with_owner_absent_marks_nothing(self):
        authors = "Irani, Ido and Morag, Jonathan"
        result = format_authors(authors, self.cfg, co_first=True)
        assert CO_FIRST_MARKER not in result

    def test_integer_marks_leading_n(self):
        """co_first=2 daggers the first two authors (incl. the owner)."""
        authors = "Irani, Ido and Li, Jiaxuan and Morag, Jonathan"
        result = format_authors(authors, self.cfg, co_first=2)
        assert "Irani I." + CO_FIRST_MARKER in result
        assert r"\textbf{Li J.}" + CO_FIRST_MARKER in result
        assert "Morag J." + CO_FIRST_MARKER not in result

    def test_integer_capped_at_total(self):
        authors = "Irani, Ido and Li, Jiaxuan"
        result = format_authors(authors, self.cfg, co_first=5)
        assert "Irani I." + CO_FIRST_MARKER in result
        assert r"\textbf{Li J.}" + CO_FIRST_MARKER in result

    def test_none_marks_nothing(self):
        authors = "Irani, Ido and Li, Jiaxuan and Morag, Jonathan"
        result = format_authors(authors, self.cfg, co_first=None)
        assert CO_FIRST_MARKER not in result

    def test_marker_via_override_in_format_entry(self):
        cfg = FormatterConfig(overrides={"k": {"co_first": 2}})
        entry = {
            "ID": "k",
            "author": "Irani, Ido and Li, Jiaxuan and Morag, Jonathan",
            "title": "{A Title}",
            "journal": r"\apj",
            "volume": "962",
            "eid": "109",
            "year": "2024",
        }
        result = format_entry(entry, cfg)
        assert "Irani I." + CO_FIRST_MARKER in result
        assert r"\textbf{Li J.}" + CO_FIRST_MARKER in result

    def test_co_first_promoted_to_first_group(self):
        """Owner listed 2nd, but co_first → lands in first-author group."""
        cfg = FormatterConfig(overrides={"k": {"co_first": 2}})
        entries = [{
            "ID": "k",
            "author": "Irani, Ido and Li, Jiaxuan and Morag, Jonathan",
            "title": "{A Title}",
            "journal": r"\apj",
            "volume": "962",
            "eid": "109",
            "year": "2024",
        }]
        output = format_entries_grouped(entries, cfg)
        assert "First-author" in output
        assert "Second/third-author" not in output
