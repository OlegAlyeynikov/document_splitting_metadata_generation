from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from pathlib import Path

import pandas as pd

from pipeline.config_loader import load_config
from pipeline.excel_handler import build_page_map, check_cross_file_invoice_collisions, load_excel
from pipeline.models import AppConfig
from pipeline.output_writer import build_output_zip, write_segment
from pipeline.pdf_handler import validate_page_count
from pipeline.segmentation import compute_segments

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split PDF documents into invoice sub-documents with paired Excel metadata."
    )
    parser.add_argument("--config", required=True, metavar="CONFIG", help="Path to config.ini")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Simulate the full pipeline without writing any files. "
            "Logs what would be created — useful for verifying configuration before a real run."
        ),
    )
    return parser.parse_args()


def _load_pdfs_from_zip(zip_path: Path) -> dict[str, bytes]:
    pdfs: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for entry in zf.namelist():
            name = Path(entry).name.lower()
            if name.endswith(".pdf"):
                pdfs[name] = zf.read(entry)
    logger.info("Extracted %d PDF(s) from %s", len(pdfs), zip_path)
    return pdfs



def _ensure_output_dirs(config: AppConfig, dry_run: bool) -> None:
    if dry_run:
        return
    config.output_pdf_dir.mkdir(parents=True, exist_ok=True)
    config.output_xls_dir.mkdir(parents=True, exist_ok=True)


def _process_file(
    filename: str,
    pdf_bytes: bytes,
    df: pd.DataFrame,
    config: AppConfig,
    dry_run: bool,
) -> int:
    filename_lower = filename.lower()
    page_map = build_page_map(df, filename_lower)

    total_pages = validate_page_count(filename_lower, pdf_bytes, page_map)
    segments = compute_segments(filename_lower, page_map, config.altro_mode, total_pages)

    if not segments:
        logger.warning("%s: skipped — no segments produced", filename)
        return 0

    for segment in segments:
        write_segment(segment, pdf_bytes, df, config, dry_run=dry_run)

    logger.info("%s → %d segment(s)", filename, len(segments))
    return len(segments)


def main() -> None:
    _setup_logging()
    args = _parse_args()

    if args.dry_run:
        logger.info("DRY RUN mode — no files will be written")

    config = load_config(args.config)
    _ensure_output_dirs(config, args.dry_run)

    df = load_excel(config.excel_file)
    check_cross_file_invoice_collisions(df)

    pdfs = _load_pdfs_from_zip(config.pdf_zip)

    excel_filenames = set(df["platform filename"].str.lower().unique())
    zip_filenames = set(pdfs.keys())

    only_in_excel = excel_filenames - zip_filenames
    only_in_zip = zip_filenames - excel_filenames
    if only_in_excel:
        logger.warning("Files in Excel but not in ZIP: %s", ", ".join(sorted(only_in_excel)))
    if only_in_zip:
        logger.warning("Files in ZIP but not in Excel: %s", ", ".join(sorted(only_in_zip)))

    total_segments = 0
    failed_files = 0

    for filename, pdf_bytes in sorted(pdfs.items()):
        if filename not in excel_filenames:
            logger.warning("%s: no Excel rows found — skipping", filename)
            continue
        try:
            count = _process_file(filename, pdf_bytes, df, config, args.dry_run)
            total_segments += count
        except Exception:
            logger.exception("Failed to process %s", filename)
            failed_files += 1

    build_output_zip(config, dry_run=args.dry_run)

    prefix = "[DRY RUN] " if args.dry_run else ""
    logger.info(
        "%sDone. %d file(s) processed, %d segment(s) produced, %d failure(s).",
        prefix,
        len(pdfs) - failed_files,
        total_segments,
        failed_files,
    )

    if failed_files:
        sys.exit(1)


if __name__ == "__main__":
    main()
