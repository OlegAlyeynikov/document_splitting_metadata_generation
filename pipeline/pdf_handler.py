from __future__ import annotations

import io
import logging
from pathlib import Path

import pikepdf

from .models import Segment

logger = logging.getLogger(__name__)


def get_pdf_page_count(pdf_bytes: bytes) -> int:
    with pikepdf.Pdf.open(io.BytesIO(pdf_bytes)) as pdf:
        return len(pdf.pages)


def validate_page_count(filename: str, pdf_bytes: bytes, page_map: dict) -> int:
    """Return the actual PDF page count and log any mismatch with the Excel."""
    actual = get_pdf_page_count(pdf_bytes)
    classified = set(page_map.keys())
    max_classified = max(classified) if classified else 0

    if actual < max_classified:
        logger.error(
            "%s: Excel references page %d but PDF only has %d pages — "
            "pages beyond the PDF end will be absent from output",
            filename,
            max_classified,
            actual,
        )
    elif actual > max_classified:
        unclassified_count = actual - len(classified)
        logger.info(
            "%s: PDF has %d pages, Excel classifies %d — %d unclassified page(s) will be "
            "attached to their preceding segment",
            filename,
            actual,
            len(classified),
            unclassified_count,
        )

    return actual


def extract_pdf_segment(pdf_bytes: bytes, segment: Segment, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pikepdf.Pdf.open(io.BytesIO(pdf_bytes)) as src:
        dst = pikepdf.Pdf.new()
        dst.pages.extend(src.pages[page_num - 1] for page_num in segment.pages)
        dst.save(str(output_path))

    logger.debug(
        "Wrote PDF: %s (%d pages from %s)",
        output_path,
        len(segment.pages),
        segment.source_file,
    )
