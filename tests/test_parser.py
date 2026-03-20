"""Tests for bib2cv.parser — BibTeX parsing."""

from __future__ import annotations

import os

from bib2cv.parser import parse_bibfile, parse_bibstring


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestParseBibfile:
    def test_parse_sample(self):
        path = os.path.join(FIXTURES_DIR, "sample.bib")
        entries = parse_bibfile(path)
        assert len(entries) == 4

        # Check that key fields are present
        keys_found = {e["ID"] for e in entries}
        assert "2026ApJ...998L..24L" in keys_found
        assert "2026ApJ...998L...6C" in keys_found

    def test_fields_present(self):
        path = os.path.join(FIXTURES_DIR, "sample.bib")
        entries = parse_bibfile(path)
        first = next(e for e in entries if e["ID"] == "2026ApJ...998L..24L")
        assert "author" in first
        assert "title" in first
        assert "Li" in first["author"]


class TestParseBibstring:
    def test_single_entry(self):
        bib = r"""
@ARTICLE{testkey,
    author = {Smith, John and Doe, Jane},
    title = {A Test Paper},
    journal = {\apj},
    year = 2025,
    volume = {100},
    pages = {1},
}
"""
        entries = parse_bibstring(bib)
        assert len(entries) == 1
        assert entries[0]["ID"] == "testkey"
        assert "Smith" in entries[0]["author"]
