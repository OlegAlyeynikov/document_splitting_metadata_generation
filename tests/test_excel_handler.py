from __future__ import annotations

import pytest

from pipeline.excel_handler import build_page_map, filter_excel_rows
from pipeline.models import Segment


def test_build_page_map_basic(sample_df_simple):
    page_map = build_page_map(sample_df_simple, "test.pdf")
    assert page_map[1].label == "Fattura"
    assert page_map[1].invoice_num == "INV-001"
    assert page_map[2].label == "Fattura"
    assert page_map[2].invoice_num == "INV-002"
    assert page_map[3].label == "Altro"
    assert page_map[3].invoice_num is None


def test_build_page_map_case_insensitive(sample_df_simple):
    page_map = build_page_map(sample_df_simple, "TEST.PDF")
    assert len(page_map) == 3


def test_build_page_map_duplicate_invoice_num_keeps_first(make_df):
    df = make_df(
        [
            {
                "platform filename": "f.pdf",
                "label container type": "page_classification",
                "label container": "Page Classification",
                "attribute": "Fattura",
                "page": 1,
            },
            {
                "platform filename": "f.pdf",
                "label container type": "entity_extraction",
                "label container": "Fattura",
                "attribute": "Numero fattura",
                "value": "FIRST",
                "page": 1,
            },
            {
                "platform filename": "f.pdf",
                "label container type": "entity_extraction",
                "label container": "Fattura",
                "attribute": "Numero fattura",
                "value": "SECOND",
                "page": 1,
            },
        ]
    )
    page_map = build_page_map(df, "f.pdf")
    assert page_map[1].invoice_num == "FIRST"


def test_filter_excel_rows_includes_document_classification(sample_df_simple):
    segment = Segment(
        source_file="test.pdf",
        pages=(1,),
        segment_type="invoice",
        invoice_num="INV-001",
        part_index=1,
    )
    result = filter_excel_rows(sample_df_simple, segment)
    types = set(result["label container type"])
    assert "document_classification" in types
    assert "page_classification" in types
    assert "entity_extraction" in types


def test_filter_excel_rows_excludes_other_pages(sample_df_simple):
    segment = Segment(
        source_file="test.pdf",
        pages=(1,),
        segment_type="invoice",
        invoice_num="INV-001",
        part_index=1,
    )
    result = filter_excel_rows(sample_df_simple, segment)
    page_rows = result[result["label container type"] == "page_classification"]
    assert set(page_rows["page"].dropna().astype(int)) == {1}


def test_filter_excel_rows_case_insensitive(sample_df_simple):
    segment = Segment(
        source_file="TEST.PDF",
        pages=(1,),
        segment_type="invoice",
        invoice_num="INV-001",
        part_index=1,
    )
    result = filter_excel_rows(sample_df_simple, segment)
    assert len(result) > 0


def test_filter_excel_rows_empty_segment_still_has_doc_class(sample_df_simple):
    segment = Segment(
        source_file="test.pdf",
        pages=(99,),
        segment_type="invoice",
        invoice_num=None,
        part_index=1,
    )
    result = filter_excel_rows(sample_df_simple, segment)
    assert (result["label container type"] == "document_classification").any()
