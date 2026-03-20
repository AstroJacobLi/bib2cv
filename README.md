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

Then your `output.tex` will be populated with the publication list. You can then include it in your CV using `\input{output.tex}`.

Example:
```latex
\item \textbf{Li J.}, Greene J.~E., Danieli S., Carlsten S.~G., Geha M., \href{https://ui.adsabs.harvard.edu/abs/2026ApJ...998L..24L}{A Possible ``Too-many-satellites'' Problem in the Isolated Dwarf Galaxy DDO 161}, \textit{ApJL} 998, L24 (2026).

\item Carlsten S., \textbf{Li J.}, Greene J., Drlica-Wagner A., Danieli S., \href{https://ui.adsabs.harvard.edu/abs/2026arXiv260216778C}{ELVES-Field: Isolated Dwarf Galaxy Quenched Fractions Rise Below $M_* \approx 10^7$ $M_\odot$}, arXiv:2602.16778.

\item Ma Y., Greene J.~E., Setton D.~J., Goulding A.~D. et al. (including \textbf{Li J.}), \href{https://ui.adsabs.harvard.edu/abs/2026ApJ..1000...59M}{Counting Little Red Dots at z < 4 with Ground-based Surveys and Spectroscopic Follow-up}, \textit{ApJ} 1000, 59 (2026).

\item \textbf{Li J.}, Carlsten S., Danieli S., Greene J.~E., Lin X., Savino A., Telford G., \href{https://ui.adsabs.harvard.edu/abs/2025hst..prop18046L}{Testing the Mass Threshold of Reionization-Quenching with Isolated Dwarf Galaxy Hedgehog}, HST Proposal (2025).
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
