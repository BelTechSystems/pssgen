# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""tests/test_req_parser.py — Unit tests for parser/req_parser.py.

Phase: v3a
Layer: 1 (parser)

Tests requirement entry parsing and waiver identification.
"""
import os
import tempfile
import pytest
from parser.req_parser import parse_req, ReqParseResult


def _write_req(content: str) -> str:
    """Write req content to a temporary file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".req", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_req_parser_reads_entries() -> None:
    """Requirement entries are parsed with correct IDs and statements."""
    content = """\
[SYS-REQ-001] Counter must reset to zero on rst_n assertion.
  verification: simulation, formal

[SYS-REQ-002] Counter must count up when enable and up_down are high.
  verification: simulation
"""
    path = _write_req(content)
    try:
        result = parse_req(path)
        assert "SYS-REQ-001" in result.requirements
        assert "SYS-REQ-002" in result.requirements

        entry_001 = result.requirements["SYS-REQ-001"]
        assert "reset" in entry_001["statement"].lower()
        assert "simulation" in entry_001["verification"]
        assert "formal" in entry_001["verification"]
        assert entry_001["waived"] is False

        entry_002 = result.requirements["SYS-REQ-002"]
        assert "count" in entry_002["statement"].lower()
        assert "simulation" in entry_002["verification"]
    finally:
        os.unlink(path)


def test_req_parser_reads_waivers() -> None:
    """Waived requirement entries are identified correctly."""
    content = """\
[SYS-REQ-003] Overflow wraps to zero.
  verification: simulation
  [WAIVED] Not applicable for this design iteration.

[SYS-REQ-004] Underflow wraps to 255.
  verification: simulation
"""
    path = _write_req(content)
    try:
        result = parse_req(path)
        assert "SYS-REQ-003" in result.waivers
        assert "SYS-REQ-004" not in result.waivers

        entry_003 = result.requirements["SYS-REQ-003"]
        assert entry_003["waived"] is True
        assert "Not applicable" in entry_003["waiver_reason"]
    finally:
        os.unlink(path)
