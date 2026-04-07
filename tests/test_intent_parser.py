# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""tests/test_intent_parser.py — Unit tests for parser/intent_parser.py.

Phase: v3a
Layer: 1 (parser)

Tests requirement ID extraction, scheme detection, disposition keyword
exclusion, waiver extraction, and the empty-IDs baseline case.
"""
import os
import tempfile
import pytest
from parser.intent_parser import parse_intent, IntentParseResult


def _write_intent(content: str) -> str:
    """Write intent content to a temporary file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".intent", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_intent_parser_extracts_req_ids() -> None:
    """Requirement IDs [SYS-REQ-047] and [FUNC-REQ-112] are extracted correctly."""
    content = """\
reset behavior:
  Apply reset low for 2 cycles. [SYS-REQ-047]

counting sequences:
  Exercise all count modes. [FUNC-REQ-112]
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert "SYS-REQ-047" in result.req_ids
        assert "FUNC-REQ-112" in result.req_ids
    finally:
        os.unlink(path)


def test_intent_parser_detects_schemes() -> None:
    """Schemes [SYS-REQ, FUNC-REQ] are detected from extracted IDs."""
    content = """\
reset behavior:
  Apply reset low. [SYS-REQ-047]
  Exercise count modes. [FUNC-REQ-112]
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert "SYS-REQ" in result.req_schemes
        assert "FUNC-REQ" in result.req_schemes
    finally:
        os.unlink(path)


def test_intent_parser_excludes_dispositions() -> None:
    """Disposition keywords [GENERATED], [CONFIRMED], [WAIVED] are not treated as IDs."""
    content = """\
port behaviors:
  [GENERATED] clk: synchronous clock — verify all synchronous behavior
  [CONFIRMED] rst_n: reset deasserts cleanly
  [WAIVED] enable: not covered in this iteration
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert "GENERATED" not in result.req_ids
        assert "CONFIRMED" not in result.req_ids
        assert "WAIVED" not in result.req_ids
    finally:
        os.unlink(path)


def test_intent_parser_extracts_waivers() -> None:
    """A [WAIVED] entry with reason is captured correctly in the waivers list."""
    content = """\
corner cases:
  [WAIVED] overflow handling not required for this revision [SYS-REQ-099]
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert len(result.waivers) == 1
        waiver = result.waivers[0]
        assert isinstance(waiver, dict)
        assert "item" in waiver
        assert "reason" in waiver
        assert "req_ids" in waiver
    finally:
        os.unlink(path)


def test_intent_parser_inline_requirements_section() -> None:
    """A [requirements] section with one entry populates inline_requirements."""
    content = """\
requirements:
[UART-BR-004] BAUD_TUNING shall only be written while UART_EN is deasserted.
  verification: Simulation
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert "UART-BR-004" in result.inline_requirements
        entry = result.inline_requirements["UART-BR-004"]
        assert "BAUD_TUNING" in entry["statement"]
        assert "Simulation" in entry["verification"]
        assert entry["waived"] is False
    finally:
        os.unlink(path)


def test_intent_parser_inline_requirements_empty_without_section() -> None:
    """An .intent file with no [requirements] section has inline_requirements == {}."""
    content = """\
reset behavior:
  Apply reset low for 2 cycles.
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert result.inline_requirements == {}
    finally:
        os.unlink(path)


def test_intent_parser_waiver_req_id_warning(capsys) -> None:
    """[WAIVED] with a req ID in a content line emits a WARNING to stderr."""
    content = """\
corner cases:
  [WAIVED] SYS-REQ-001 Cannot test this pre-silicon.
"""
    path = _write_intent(content)
    try:
        parse_intent(path)
        captured = capsys.readouterr()
        assert "SYS-REQ-001" in captured.err
        assert "WARNING" in captured.err
    finally:
        os.unlink(path)


def test_intent_parser_no_req_ids() -> None:
    """A file with no requirement IDs returns an empty req_ids list."""
    content = """\
reset behavior:
  Apply reset low for 2 cycles.
  Count must be zero after reset.

counting sequences:
  Exercise up and down counting.
"""
    path = _write_intent(content)
    try:
        result = parse_intent(path)
        assert result.req_ids == []
        assert result.req_schemes == []
    finally:
        os.unlink(path)
