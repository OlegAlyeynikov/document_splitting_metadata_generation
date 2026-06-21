from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

import pikepdf


def _make_minimal_pdf(num_pages: int = 1) -> bytes:
    buf = io.BytesIO()
    pdf = pikepdf.Pdf.new()
    for _ in range(num_pages):
        page = pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
            Resources=pikepdf.Dictionary(),
            Contents=pikepdf.Stream(pdf, b""),
        )
        pdf.pages.append(page)
    pdf.save(buf)
    return buf.getvalue()


COLUMNS = [
    "platform filename",
    "document",
    "page",
    "project id",
    "flow execution id",
    "annotation id",
    "label container type",
    "label container",
    "attribute",
    "value",
    "accuracy",
    "validation",
    "extraction date",
    "link",
    "CLIENT_FILE_ID",
    "entity_progr",
]


def make_pdf_bytes(num_pages: int = 1) -> bytes:
    return _make_minimal_pdf(num_pages)


def make_dataframe(rows: list[dict]) -> pd.DataFrame:
    records = []
    for r in rows:
        record = {col: None for col in COLUMNS}
        record.update(r)
        records.append(record)
    df = pd.DataFrame(records, columns=COLUMNS)
    df["page"] = pd.array(df["page"], dtype="Int64")
    return df


@pytest.fixture()
def make_df():
    """Return the make_dataframe factory so tests can build custom DataFrames."""
    return make_dataframe


@pytest.fixture()
def sample_pdf_3pages() -> bytes:
    return make_pdf_bytes(3)


@pytest.fixture()
def sample_df_simple() -> pd.DataFrame:
    return make_dataframe(
        [
            {
                "platform filename": "test.pdf",
                "label container type": "document_classification",
                "label container": "Document Classification",
                "attribute": "Fattura",
                "value": "test.pdf",
                "page": None,
            },
            {
                "platform filename": "test.pdf",
                "label container type": "page_classification",
                "label container": "Page Classification",
                "attribute": "Fattura",
                "value": "test.pdf",
                "page": 1,
            },
            {
                "platform filename": "test.pdf",
                "label container type": "entity_extraction",
                "label container": "Fattura",
                "attribute": "Numero fattura",
                "value": "INV-001",
                "page": 1,
            },
            {
                "platform filename": "test.pdf",
                "label container type": "page_classification",
                "label container": "Page Classification",
                "attribute": "Fattura",
                "value": "test.pdf",
                "page": 2,
            },
            {
                "platform filename": "test.pdf",
                "label container type": "entity_extraction",
                "label container": "Fattura",
                "attribute": "Numero fattura",
                "value": "INV-002",
                "page": 2,
            },
            {
                "platform filename": "test.pdf",
                "label container type": "page_classification",
                "label container": "Page Classification",
                "attribute": "Altro",
                "value": "test.pdf",
                "page": 3,
            },
        ]
    )
