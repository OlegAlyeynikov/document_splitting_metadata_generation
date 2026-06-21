# Document Splitting & Metadata Generation Pipeline

Splits PDF documents into invoice sub-documents based on page classification data from an Excel
extraction file, and produces a paired Excel metadata file for each generated sub-document.

## Why pikepdf

PDF splitting can be done with several Python libraries. The most common options are `pypdf`,
`PyMuPDF` (fitz), and `pikepdf`. This project uses `pikepdf` for one main reason: **it copies
pages without re-rendering them**.

When you split a PDF with most libraries, the pages go through a decode-and-encode cycle. This
can change the visual quality of scanned documents, alter embedded fonts, or slightly modify
the file structure. For invoice documents — where pixel-perfect fidelity and legal integrity
matter — this is not acceptable.

`pikepdf` works at the object level. It reads the raw PDF structure and moves page objects
directly from source to destination without touching the content. The output pages are
byte-for-byte identical to the originals. This is sometimes called *lossless* splitting.

A secondary benefit is performance. Because there is no rendering step, splitting a 100-page
PDF takes milliseconds rather than seconds, even for large scanned files.

`pypdf` was considered as a fallback option, but it does not guarantee lossless output for all
PDF variants. `PyMuPDF` is faster for rendering use cases but is licensed under AGPL, which
adds legal complexity. `pikepdf` uses a permissive MIT-like license and is the standard choice
for lossless PDF manipulation in Python.

## Prerequisites

- Python 3.11+

## Installation

```bash
# Install uv if not already available
pip install uv

# Create virtual environment and install all dependencies
uv sync
```

## Configuration

All parameters are in `config.ini`. No paths are hard-coded in the script.

```ini
[paths]
excel_file     = ./assignment_test/output_test.xlsx   # input Excel
pdf_zip        = ./assignment_test/pdf_test_immagini.zip  # input ZIP with PDFs
output_pdf_dir = ./output/pdfs    # where split PDFs are written
output_xls_dir = ./output/excels  # where split Excel files are written
output_zip     = ./output/result.zip  # final ZIP collecting all outputs

[processing]
altro_mode = split   # discard | split | group
```

### `altro_mode` values

| Mode | Behaviour |
|---|---|
| `discard` | Pages classified as *Altro* are excluded from all outputs |
| `split` | Each contiguous run of *Altro* pages becomes its own sub-document with a paired Excel |
| `group` | All *Altro* pages of a source PDF are collected into one additional sub-document |

## Running

```bash
# Normal run
uv run python split_documents.py --config config.ini

# Dry run — simulates the full pipeline, logs what would be created, writes nothing
uv run python split_documents.py --config config.ini --dry-run
```

### Why `--dry-run`?

Use it to verify your configuration and understand how the pipeline will split the documents
**before** committing to writing hundreds of files. The log output shows exactly which segments
would be produced, which pages they contain, and any warnings (missing invoice numbers, page
count mismatches, duplicate invoice numbers across files). It is safe to run multiple times.

## Output

For each source PDF the script produces pairs of files:

```
{stem}_part01.pdf / {stem}_part01.xlsx   ← invoice sub-document (Fattura pages)
{stem}_part02.pdf / {stem}_part02.xlsx
...
{stem}_altro.pdf  / {stem}_altro.xlsx    ← Altro pages in group mode
{stem}_altro.pdf  / {stem}_altro.xlsx    ← first Altro run in split mode
{stem}_altro_02.pdf / {stem}_altro_02.xlsx ← second Altro run in split mode
{stem}_unclassified.pdf / {stem}_unclassified.xlsx ← pages absent from Excel (if any)
```

The `_part{N}` suffix is used for invoice sub-documents. Altro sub-documents use `_altro` /
`_altro_{N}` suffixes to make the document type immediately readable in a directory listing.
Every PDF is paired with an identically named XLSX. All files are collected into `output_zip`.

## Running Tests

```bash
uv run pytest -v
```

## Edge Cases and Decisions

### Pages classified as Fattura but without a `Numero fattura`
50 such pages exist in the test data. These are treated as continuation pages of the current
invoice (same `invoice_num`). A `WARNING` is logged for each.

### Unclassified pages (PDF pages not referenced in the Excel)
Every source PDF in the test data contains pages not described in the Excel — the pipeline
attaches them to the preceding segment. Rationale: they are almost always overflow or
continuation pages. A `WARNING` is logged with the page number.

### Files not starting with a Fattura page
If the first classified page is *Altro*, it is handled according to `altro_mode`. If the file
has no Fattura pages at all, no segments are produced and a `WARNING` is logged.

### Duplicate invoice numbers across files
`TIM00861`, `ΤΙΜ00860`, `5043`, and `144` appear in multiple source PDFs. This does not affect
output naming (each output is scoped to its source file stem). A `WARNING` is logged to flag
the anomaly for investigation.

### Multiple `Numero fattura` on the same page
`41.pdf` page 1 has two extracted invoice numbers. The first one is used; the second is
discarded with a `WARNING`.

### Page count mismatch
If the Excel references a page number higher than the actual PDF page count, an `ERROR` is
logged. Processing continues — Excel rows referencing pages beyond the PDF end will be absent
from the output, but all valid pages are still extracted normally.

## Project Structure

```
split_documents.py      # CLI entry point and orchestration
pipeline/               # core package
  models.py             # Frozen dataclasses: Segment, PageInfo, AppConfig
  config_loader.py      # INI parsing and validation
  excel_handler.py      # Excel read, page map building, row filtering, write
  segmentation.py       # Core splitting algorithm (pure function, no IO)
  pdf_handler.py        # PDF page extraction via pikepdf
  output_writer.py      # Naming convention, write loose files, build ZIP
tests/                  # pytest unit tests
config.ini              # Configuration template
pyproject.toml          # Project metadata and dependencies (uv)
uv.lock                 # Locked dependency versions
```
