# bib2cv

Convert a BibTeX file of publications into LaTeX `\item` entries for an academic CV. Optimized for astrophysicists.

## Installation

```bash
pip install -e .
```

## Usage
First, you need to have a personal ADS library on [ADS](https://ui.adsabs.harvard.edu/). Then you can export the BibTeX file to a local file, say `pubs.bib`. To get a publication list in Latex for your CV, you can use the following command:

```bash
# Grouped output (default: first-author, 2nd/3rd, other, misc)
bib2cv pubs.bib -o output.tex

# With per-entry overrides
bib2cv pubs.bib --overrides overrides.json -o output.tex

# Flat list (no grouping)
bib2cv pubs.bib --no-group
```

### CLI Options

| Flag             | Default        | Description                                    |
|------------------|----------------|------------------------------------------------|
| `-o`             | stdout         | Output file path                               |
| `--author`       | `Li, Jiaxuan`  | Name to bold, in `Last, First` format          |
| `--overrides`    | —              | JSON file for per-entry overrides              |
| `--max-position` | `5`            | Author position threshold for truncation       |
| `--no-group`     | off            | Output a flat list instead of grouped sections |
| `--no-sort`      | off            | Disable reverse-chronological sorting          |

## Overrides

A JSON file mapping BibTeX keys to per-entry overrides:

```json
{
    "2025arXiv250408030L": {
        "status": "accepted",
        "journal": "ApJ"
    },
    "2026arXiv260221280H": {
        "description": "white paper for Roman Cycle 1"
    },
    "2024AAS...24326110L": {
        "description": "AAS abstract (2024)"
    }
}
```

**Override fields:**

- `"status"` — force status: `"published"`, `"accepted"`, `"submitted"`, `"arxiv"`, `"in prep"`
- `"journal"` — override the journal name (e.g., `"ApJ"`, `"ApJL"`)
- `"description"` — routes the entry to the **misc** group with a custom label (e.g., proposals, abstracts, white papers). ArXiv numbers are appended automatically when available.

For `accepted` and `submitted` entries, the arXiv number is shown automatically when present in the BibTeX.

## Misc entries

Entries are auto-detected as misc (and grouped separately) if they are:
- `MISC` or `INPROCEEDINGS` BibTeX types, or
- ADS keys matching patterns like `AAS`, `prop`, `conf`, `mpec`, or
- given a `"description"` override.

## Python API

```python
from bib2cv import parse_bibfile, format_entries_grouped
from bib2cv.formatter import FormatterConfig

entries = parse_bibfile("pubs.bib")
cfg = FormatterConfig(
    owner_last="Li", owner_first="Jiaxuan",
    overrides={"key": {"status": "accepted", "journal": "ApJ"}},
)
print(format_entries_grouped(entries, cfg))
```

## Tests

```bash
pip install -e ".[test]"
python -m pytest tests/ -v
```
