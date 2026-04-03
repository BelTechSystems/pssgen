# ===========================================================
# FILE:         tests/test_regmap_parser.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for parser/regmap_parser.py and the resolve_regmap_file()
#   function in parser/context.py. Exercises .xlsx parsing against the
#   counter_regmap gold fixture, example row filtering, field normalisation,
#   and plain English register map section parsing.
#
# LAYER:        1 — parser
# PHASE:        v4a
#
# FUNCTIONS:
#   (test functions — no public API)
#
# DEPENDENCIES:
#   Standard library:  os, tempfile
#   Internal:          parser.regmap_parser, parser.context
#
# HISTORY:
#   v4a   2026-04-03  SB  Initial implementation; 14 tests covering xlsx, plain English, and context
#
# ===========================================================
"""tests/test_regmap_parser.py — Unit tests for register map parser and context resolver.

Phase: v4a
Layer: 1 (parser)

Tests XLSX parsing (counter_regmap gold fixture), example row filtering,
field normalization, plain English register map section parsing, and the
resolve_regmap_file() auto-detection logic.
"""
import os
import tempfile
import pytest

from parser.regmap_parser import parse_regmap, _parse_intent_regmap
from parser.context import resolve_regmap_file

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
COUNTER_REGMAP = os.path.join(FIXTURES, "counter_regmap.xlsx")
TEMPLATE_REGMAP = os.path.join(
    os.path.dirname(__file__), "..", "docs", "pssgen_regmap_template.xlsx"
)
INTENT_WITH_REGMAP = os.path.join(FIXTURES, "intent_with_regmap.intent")


# ---------------------------------------------------------------------------
# XLSX parsing tests — counter_regmap gold fixture
# ---------------------------------------------------------------------------

def test_regmap_parser_loads_globals() -> None:
    """Globals sheet is parsed and project_name is up_down_counter."""
    result = parse_regmap(COUNTER_REGMAP)
    assert result["globals"]["project_name"] == "up_down_counter"


def test_regmap_parser_loads_blocks() -> None:
    """Blocks sheet contains exactly one entry with block_name COUNTER."""
    result = parse_regmap(COUNTER_REGMAP)
    blocks = result["blocks"]
    assert len(blocks) == 1
    assert blocks[0]["block_name"] == "COUNTER"


def test_regmap_parser_loads_registers() -> None:
    """RegisterMap groups into exactly 5 register entries."""
    result = parse_regmap(COUNTER_REGMAP)
    assert len(result["registers"]) == 5


def test_regmap_parser_loads_fields() -> None:
    """Total field count across all registers is 15."""
    result = parse_regmap(COUNTER_REGMAP)
    total = sum(len(r["fields"]) for r in result["registers"])
    assert total == 15


def test_regmap_parser_field_normalization_volatile() -> None:
    """STATUS.RUNNING has volatile=True (YES → True conversion)."""
    result = parse_regmap(COUNTER_REGMAP)
    status_reg = next(r for r in result["registers"] if r["name"] == "STATUS")
    running = next(f for f in status_reg["fields"] if f["field_name"] == "RUNNING")
    assert running["volatile"] is True


def test_regmap_parser_field_normalization_coverage() -> None:
    """CTRL.ENABLE has uvm_has_coverage=True; LOAD.RESERVED has uvm_has_coverage=False."""
    result = parse_regmap(COUNTER_REGMAP)
    ctrl_reg = next(r for r in result["registers"] if r["name"] == "CTRL")
    enable_field = next(f for f in ctrl_reg["fields"] if f["field_name"] == "ENABLE")
    assert enable_field["uvm_has_coverage"] is True

    load_reg = next(r for r in result["registers"] if r["name"] == "LOAD")
    reserved = next(f for f in load_reg["fields"] if f["field_name"] == "RESERVED")
    assert reserved["uvm_has_coverage"] is False


def test_regmap_parser_req_id_preserved() -> None:
    """CTRL.ENABLE field carries req_id FUNC-REQ-201."""
    result = parse_regmap(COUNTER_REGMAP)
    ctrl_reg = next(r for r in result["registers"] if r["name"] == "CTRL")
    enable_field = next(f for f in ctrl_reg["fields"] if f["field_name"] == "ENABLE")
    assert enable_field["req_id"] == "FUNC-REQ-201"


def test_regmap_parser_enum_loaded() -> None:
    """Enums dict contains counter_dir_t with 2 entries."""
    result = parse_regmap(COUNTER_REGMAP)
    assert "counter_dir_t" in result["enums"]
    assert len(result["enums"]["counter_dir_t"]) == 2


def test_regmap_parser_skips_example_rows() -> None:
    """Template workbook example rows are skipped; registers list is empty."""
    result = parse_regmap(TEMPLATE_REGMAP)
    assert len(result["registers"]) == 0


def test_regmap_parser_reserved_field_access_na() -> None:
    """COUNT.RESERVED field has access=NA."""
    result = parse_regmap(COUNTER_REGMAP)
    count_reg = next(r for r in result["registers"] if r["name"] == "COUNT")
    reserved = next(f for f in count_reg["fields"] if f["field_name"] == "RESERVED")
    assert reserved["access"] == "NA"


# ---------------------------------------------------------------------------
# Plain English parsing tests
# ---------------------------------------------------------------------------

_PLAIN_ENGLISH_CONTENT = """\
reset behavior:
  Apply rst_n low for 2 cycles.

register map:
  CTRL register at offset 0x00:
    ENABLE field [0:0] RW reset=0 — enable the core
    MODE field [2:1] RW reset=1 — operating mode

  STATUS register at offset 0x04 (volatile):
    TX_READY field [0:0] RO — transmit ready flag

coverage goals:
  Register reads and writes exercised.
"""


def test_regmap_parser_plain_english_basic() -> None:
    """Plain English content with two registers produces registers list of length 2."""
    result = _parse_intent_regmap(_PLAIN_ENGLISH_CONTENT)
    assert len(result["registers"]) == 2


def test_regmap_parser_plain_english_field_bits() -> None:
    """MODE field [2:1] gives bit_offset=1, bit_width=2."""
    result = _parse_intent_regmap(_PLAIN_ENGLISH_CONTENT)
    ctrl_reg = next(r for r in result["registers"] if r["name"] == "CTRL")
    mode_field = next(f for f in ctrl_reg["fields"] if f["field_name"] == "MODE")
    assert mode_field["bit_offset"] == 1
    assert mode_field["bit_width"] == 2


# ---------------------------------------------------------------------------
# resolve_regmap_file() tests
# ---------------------------------------------------------------------------

def _make_temp_dir_with_files(filenames: list[str]) -> tuple[str, str]:
    """Create a temp directory, populate it with empty files, return (dir, counter.vhd path)."""
    tmp = tempfile.mkdtemp()
    input_file = os.path.join(tmp, "counter.vhd")
    for name in filenames:
        open(os.path.join(tmp, name), "w").close()
    return tmp, input_file


def test_context_resolve_regmap_detects_stem_regmap() -> None:
    """resolve_regmap_file returns <stem>_regmap.xlsx when it exists alongside input."""
    tmp, input_file = _make_temp_dir_with_files(["counter.vhd", "counter_regmap.xlsx"])
    try:
        resolved = resolve_regmap_file(input_file)
        assert resolved is not None
        assert resolved.endswith("counter_regmap.xlsx")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def test_context_resolve_regmap_returns_none_when_absent() -> None:
    """resolve_regmap_file returns None when no xlsx file is present."""
    tmp, input_file = _make_temp_dir_with_files(["counter.vhd"])
    try:
        resolved = resolve_regmap_file(input_file)
        assert resolved is None
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
