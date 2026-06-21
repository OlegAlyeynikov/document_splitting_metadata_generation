from __future__ import annotations

import configparser
import sys
from pathlib import Path

from .models import AppConfig

_SECTION = "paths"
_PROC_SECTION = "processing"
_VALID_ALTRO_MODES = {"discard", "split", "group"}

_REQUIRED_PATHS = {
    "excel_file",
    "pdf_zip",
    "output_pdf_dir",
    "output_xls_dir",
    "output_zip",
}


def load_config(config_path: str) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        _abort(f"Config file not found: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    _require_section(parser, _SECTION, config_path)
    _require_section(parser, _PROC_SECTION, config_path)

    missing = _REQUIRED_PATHS - set(parser.options(_SECTION))
    if missing:
        _abort(f"Missing keys in [{_SECTION}]: {', '.join(sorted(missing))}")

    excel_file = Path(parser.get(_SECTION, "excel_file"))
    pdf_zip = Path(parser.get(_SECTION, "pdf_zip"))
    output_pdf_dir = Path(parser.get(_SECTION, "output_pdf_dir"))
    output_xls_dir = Path(parser.get(_SECTION, "output_xls_dir"))
    output_zip = Path(parser.get(_SECTION, "output_zip"))

    if not excel_file.exists():
        _abort(f"Excel file not found: {excel_file}")
    if not pdf_zip.exists():
        _abort(f"PDF ZIP not found: {pdf_zip}")

    altro_mode = parser.get(_PROC_SECTION, "altro_mode", fallback="").strip().lower()
    if altro_mode not in _VALID_ALTRO_MODES:
        _abort(
            f"Invalid altro_mode '{altro_mode}'. "
            f"Must be one of: {', '.join(sorted(_VALID_ALTRO_MODES))}"
        )

    return AppConfig(
        excel_file=excel_file,
        pdf_zip=pdf_zip,
        output_pdf_dir=output_pdf_dir,
        output_xls_dir=output_xls_dir,
        output_zip=output_zip,
        altro_mode=altro_mode,
    )


def _require_section(parser: configparser.ConfigParser, section: str, path: str) -> None:
    if not parser.has_section(section):
        _abort(f"Missing section [{section}] in {path}")


def _abort(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)
