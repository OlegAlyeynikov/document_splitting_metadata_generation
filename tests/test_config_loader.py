from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.config_loader import load_config


def _write_ini(tmp_path: Path, content: str) -> str:
    cfg = tmp_path / "config.ini"
    cfg.write_text(content, encoding="utf-8")
    return str(cfg)


def _valid_ini(tmp_path: Path, altro_mode: str = "split") -> str:
    excel = tmp_path / "data.xlsx"
    excel.touch()
    pdf_zip = tmp_path / "pdfs.zip"
    pdf_zip.touch()
    return _write_ini(
        tmp_path,
        f"""
[paths]
excel_file = {excel}
pdf_zip = {pdf_zip}
output_pdf_dir = {tmp_path}/out_pdf
output_xls_dir = {tmp_path}/out_xls
output_zip = {tmp_path}/result.zip

[processing]
altro_mode = {altro_mode}
""",
    )


def test_valid_config_loads(tmp_path):
    cfg_path = _valid_ini(tmp_path)
    config = load_config(cfg_path)
    assert config.altro_mode == "split"


def test_all_altro_modes_accepted(tmp_path):
    for mode in ("discard", "split", "group"):
        cfg_path = _valid_ini(tmp_path, altro_mode=mode)
        config = load_config(cfg_path)
        assert config.altro_mode == mode


def test_missing_config_file_exits():
    with pytest.raises(SystemExit):
        load_config("/nonexistent/config.ini")


def test_missing_section_exits(tmp_path):
    cfg_path = _write_ini(tmp_path, "[processing]\naltro_mode = split\n")
    with pytest.raises(SystemExit):
        load_config(cfg_path)


def test_missing_key_exits(tmp_path):
    excel = tmp_path / "data.xlsx"
    excel.touch()
    cfg_path = _write_ini(
        tmp_path,
        f"""
[paths]
excel_file = {excel}
[processing]
altro_mode = split
""",
    )
    with pytest.raises(SystemExit):
        load_config(cfg_path)


def test_invalid_altro_mode_exits(tmp_path):
    cfg_path = _valid_ini(tmp_path, altro_mode="unknown")
    with pytest.raises(SystemExit):
        load_config(cfg_path)


def test_nonexistent_excel_exits(tmp_path):
    pdf_zip = tmp_path / "pdfs.zip"
    pdf_zip.touch()
    cfg_path = _write_ini(
        tmp_path,
        f"""
[paths]
excel_file = /nonexistent/file.xlsx
pdf_zip = {pdf_zip}
output_pdf_dir = {tmp_path}/out_pdf
output_xls_dir = {tmp_path}/out_xls
output_zip = {tmp_path}/result.zip

[processing]
altro_mode = split
""",
    )
    with pytest.raises(SystemExit):
        load_config(cfg_path)
