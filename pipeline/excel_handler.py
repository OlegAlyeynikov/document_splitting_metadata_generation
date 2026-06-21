from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .models import PageInfo, Segment

logger = logging.getLogger(__name__)

_COL_FILE = "platform filename"
_COL_PAGE = "page"
_COL_TYPE = "label container type"
_COL_CONTAINER = "label container"
_COL_ATTR = "attribute"
_COL_VALUE = "value"

_TYPE_DOC_CLASS = "document_classification"
_TYPE_PAGE_CLASS = "page_classification"
_TYPE_ENTITY = "entity_extraction"


def load_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, dtype={_COL_PAGE: "Int64"}, engine="openpyxl")
    logger.info("Loaded Excel: %d rows, %d columns from %s", len(df), len(df.columns), path)
    return df


def build_page_map(df: pd.DataFrame, filename: str) -> dict[int, PageInfo]:
    file_df = df[df[_COL_FILE].str.lower() == filename.lower()]

    # --- invoice numbers (vectorized) ---
    entity_mask = (
        (file_df[_COL_TYPE] == _TYPE_ENTITY)
        & (file_df[_COL_CONTAINER] == "Fattura")
        & (file_df[_COL_ATTR] == "Numero fattura")
        & file_df[_COL_PAGE].notna()
    )
    entity_df = file_df.loc[entity_mask].copy()
    entity_df[_COL_PAGE] = entity_df[_COL_PAGE].astype(int)

    dup_pages = entity_df[entity_df.duplicated(subset=[_COL_PAGE], keep=False)]
    for page_num, group in dup_pages.groupby(_COL_PAGE):
        values = group[_COL_VALUE].astype(str).str.strip().tolist()
        logger.warning(
            "%s page %d: multiple 'Numero fattura' found (%r and %r) — keeping first",
            filename,
            page_num,
            values[0],
            values[1] if len(values) > 1 else "?",
        )

    entity_df = entity_df.drop_duplicates(subset=[_COL_PAGE], keep="first")
    invoice_nums: dict[int, str] = dict(
        zip(entity_df[_COL_PAGE], entity_df[_COL_VALUE].astype(str).str.strip())
    )

    # --- page classifications (vectorized) ---
    pc_mask = (file_df[_COL_TYPE] == _TYPE_PAGE_CLASS) & file_df[_COL_PAGE].notna()
    pc_df = file_df.loc[pc_mask].copy()
    pc_df[_COL_PAGE] = pc_df[_COL_PAGE].astype(int)

    page_map: dict[int, PageInfo] = {
        int(page): PageInfo(
            label=str(attr).strip(),
            invoice_num=invoice_nums.get(int(page)),
        )
        for page, attr in zip(pc_df[_COL_PAGE], pc_df[_COL_ATTR])
    }

    return page_map


def filter_excel_rows(df: pd.DataFrame, segment: Segment) -> pd.DataFrame:
    filename_lower = segment.source_file.lower()
    pages_set = set(segment.pages)

    file_mask = df[_COL_FILE].str.lower() == filename_lower

    doc_class_mask = file_mask & (df[_COL_TYPE] == _TYPE_DOC_CLASS)

    page_mask = file_mask & df[_COL_PAGE].isin(pages_set)

    combined = df[doc_class_mask | page_mask].copy()
    return combined.reset_index(drop=True)


def check_cross_file_invoice_collisions(df: pd.DataFrame) -> None:
    mask = (
        (df[_COL_TYPE] == _TYPE_ENTITY)
        & (df[_COL_CONTAINER] == "Fattura")
        & (df[_COL_ATTR] == "Numero fattura")
    )
    entity_df = df.loc[mask, [_COL_VALUE, _COL_FILE]].copy()
    entity_df[_COL_VALUE] = entity_df[_COL_VALUE].astype(str).str.strip()

    collision_counts = entity_df.groupby(_COL_VALUE)[_COL_FILE].nunique()
    collisions = collision_counts[collision_counts > 1].index

    for invoice_num in collisions:
        files = sorted(entity_df.loc[entity_df[_COL_VALUE] == invoice_num, _COL_FILE].unique())
        logger.warning(
            "Invoice number %r appears in multiple source files: %s",
            invoice_num,
            ", ".join(files),
        )


def write_excel(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False, engine="openpyxl")
    logger.debug("Wrote Excel: %s (%d rows)", output_path, len(df))
