# ===========================================================
# FILE:         tests/test_docx_req_parser.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
"""Tests for parser/docx_req_parser.py against the real BALU-RS-001.docx fixture."""
import os

import pytest

from parser.docx_req_parser import parse_docx_requirements

FIXTURE = os.path.join(
    os.path.dirname(__file__),
    "..", "ip", "buffered_axi_lite_uart", "docs", "BALU-RS-001.docx"
)


@pytest.fixture(scope="module")
def parsed():
    """Parse BALU-RS-001.docx once for the entire module."""
    return parse_docx_requirements(FIXTURE)


def test_docx_req_parser_finds_131_requirements(parsed):
    # >= 131 paragraph requirements + any VCRM-only range entries
    assert len(parsed.requirements) >= 131


def test_docx_req_parser_br004_present(parsed):
    assert "UART-BR-004" in parsed.req_ids
    entry = parsed.requirements["UART-BR-004"]
    assert "BAUD_TUNING" in entry["statement"]
    assert "UART_EN" in entry["statement"]
    assert entry["verification"] == ["simulation"]


def test_docx_req_parser_br004_not_waived(parsed):
    entry = parsed.requirements["UART-BR-004"]
    assert entry["waived"] is False
    assert entry["waiver_reason"] == ""


def test_docx_req_parser_verification_methods_populated(parsed):
    populated = sum(
        1 for e in parsed.requirements.values() if e["verification"]
    )
    assert populated >= 80


def test_docx_req_parser_source_file_recorded(parsed):
    assert parsed.source_file == FIXTURE


def test_docx_req_parser_ids_in_order(parsed):
    assert parsed.req_ids[0] == "UART-PAR-001"


def test_docx_req_parser_ver_statements_populated(parsed):
    ver_entries = {k: v for k, v in parsed.requirements.items() if "UART-VER-" in k}
    assert len(ver_entries) == 10, f"Expected 10 UART-VER entries, got {len(ver_entries)}"
    for req_id, entry in ver_entries.items():
        assert entry["statement"], f"{req_id} has empty statement"


def test_docx_req_parser_no_range_entries(parsed):
    range_keys = [k for k in parsed.requirements if "\u2013" in k or "\u2014" in k]
    assert range_keys == [], f"Range entries present: {range_keys}"
