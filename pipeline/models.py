from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageInfo:
    label: str
    invoice_num: str | None


@dataclass(frozen=True)
class Segment:
    source_file: str
    pages: tuple[int, ...]
    segment_type: str
    invoice_num: str | None
    part_index: int


@dataclass(frozen=True)
class AppConfig:
    excel_file: Path
    pdf_zip: Path
    output_pdf_dir: Path
    output_xls_dir: Path
    output_zip: Path
    altro_mode: str
