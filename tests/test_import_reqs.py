# ===========================================================
# FILE:         tests/test_import_reqs.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
"""Tests for commands/import_reqs.py — import-reqs subcommand."""
import os
import types

import pytest

from commands.import_reqs import run_import_reqs
from parser.req_parser import parse_req

DOCX_FIXTURE = os.path.join(
    os.path.dirname(__file__),
    "..", "ip", "buffered_axi_lite_uart", "docs", "BALU-RS-001.docx"
)


def _make_args(source=None, output=None, from_format="word"):
    """Build a minimal args namespace for run_import_reqs."""
    return types.SimpleNamespace(
        source=source,
        output=output,
        from_format=from_format,
        output_dir=None,
    )


def test_import_reqs_creates_req_file(tmp_path):
    out_path = str(tmp_path / "test_output.req")
    args = _make_args(source=DOCX_FIXTURE, output=out_path)
    rc = run_import_reqs(args)
    assert rc == 0
    assert os.path.isfile(out_path)
    content = open(out_path, encoding="utf-8").read()
    assert "[UART-BR-004]" in content
    assert "[GENERATED]" in content
    assert "verification: simulation" in content


def test_import_reqs_refuses_to_overwrite(tmp_path):
    out_path = str(tmp_path / "existing.req")
    # Pre-create the file with sentinel content
    with open(out_path, "w") as fh:
        fh.write("sentinel content\n")

    args = _make_args(source=DOCX_FIXTURE, output=out_path)
    rc = run_import_reqs(args)
    assert rc == 1
    # File must be unchanged
    assert open(out_path).read() == "sentinel content\n"


def test_import_reqs_req_file_contains_header_comments(tmp_path):
    out_path = str(tmp_path / "header_test.req")
    args = _make_args(source=DOCX_FIXTURE, output=out_path)
    rc = run_import_reqs(args)
    assert rc == 0
    content = open(out_path, encoding="utf-8").read()
    assert content.startswith("# requirements:")
    assert "# NOTE: Never overwritten by pssgen." in content


def test_import_reqs_br004_gap_demo_note_present(tmp_path):
    out_path = str(tmp_path / "gap_demo.req")
    args = _make_args(source=DOCX_FIXTURE, output=out_path)
    rc = run_import_reqs(args)
    assert rc == 0
    content = open(out_path, encoding="utf-8").read()
    assert "UART-BR-004" in content
    assert "gap demo" in content


def test_import_reqs_all_entries_generated_disposition(tmp_path):
    out_path = str(tmp_path / "dispositions.req")
    args = _make_args(source=DOCX_FIXTURE, output=out_path)
    rc = run_import_reqs(args)
    assert rc == 0
    parsed = parse_req(out_path)
    assert len(parsed.requirements) > 0
    assert all(not entry["waived"] for entry in parsed.requirements.values())
