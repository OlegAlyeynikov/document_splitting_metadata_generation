from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import pandas as pd

from .excel_handler import filter_excel_rows, write_excel
from .models import AppConfig, Segment
from .pdf_handler import extract_pdf_segment

logger = logging.getLogger(__name__)


def resolve_output_stem(segment: Segment) -> str:
    base = Path(segment.source_file).stem

    if segment.segment_type == "invoice":
        return f"{base}_part{segment.part_index:02d}"

    if segment.segment_type == "altro":
        if segment.part_index == 1:
            return f"{base}_altro"
        return f"{base}_altro_{segment.part_index:02d}"

    return f"{base}_unclassified"


def write_segment(
    segment: Segment,
    pdf_bytes: bytes,
    df: pd.DataFrame,
    config: AppConfig,
    dry_run: bool = False,
) -> tuple[Path, Path]:
    stem = resolve_output_stem(segment)
    pdf_out = config.output_pdf_dir / f"{stem}.pdf"
    xls_out = config.output_xls_dir / f"{stem}.xlsx"

    if dry_run:
        logger.info(
            "[DRY RUN] would write: %s (pages %s) + %s",
            pdf_out.name,
            _format_pages(segment.pages),
            xls_out.name,
        )
        return pdf_out, xls_out

    extract_pdf_segment(pdf_bytes, segment, pdf_out)

    segment_df = filter_excel_rows(df, segment)
    write_excel(segment_df, xls_out)

    return pdf_out, xls_out


def build_output_zip(config: AppConfig, dry_run: bool = False) -> None:
    if dry_run:
        logger.info("[DRY RUN] would create ZIP: %s", config.output_zip)
        return

    config.output_zip.parent.mkdir(parents=True, exist_ok=True)

    collected: list[Path] = []
    for directory in (config.output_pdf_dir, config.output_xls_dir):
        if directory.exists():
            collected.extend(directory.iterdir())

    with zipfile.ZipFile(config.output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(collected):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.name)

    logger.info("Created ZIP: %s (%d files)", config.output_zip, len(collected))


def _format_pages(pages: tuple[int, ...]) -> str:
    if len(pages) <= 6:
        return str(list(pages))
    return f"{list(pages[:3])}...{list(pages[-3:])} ({len(pages)} total)"
