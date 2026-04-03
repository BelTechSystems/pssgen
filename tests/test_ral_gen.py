# ===========================================================
# FILE:         tests/test_ral_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/ral_gen.py. Exercises three-artifact generation,
#   empty-register-map guard, structural content of each artifact, reserved
#   field exclusion, and endianness normalisation.
#
# LAYER:        3 — agents
# PHASE:        v4b
#
# FUNCTIONS:
#   (test functions — no public API)
#
# DEPENDENCIES:
#   Standard library:  os
#   Internal:          agents.ral_gen, ir, parser.regmap_parser
#
# HISTORY:
#   v4b   2026-04-03  SB  Initial implementation; 12 tests covering RAL generation
#
# ===========================================================
"""tests/test_ral_gen.py — Unit tests for UVM RAL generation agent.

Phase: v4b
Layer: 3 (agents)

Tests three-artifact generation, guard against None register_map,
structural content checks for all three templates, reserved field
exclusion, and endianness context normalisation.
"""
import os
import pytest

from ir import IR, Port
from agents.ral_gen import generate_ral, _build_ral_context
from parser.regmap_parser import parse_regmap

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
COUNTER_REGMAP = os.path.join(FIXTURES, "counter_regmap.xlsx")


def _make_ir_with_regmap() -> IR:
    """Return a minimal IR populated with the counter_regmap gold fixture."""
    ir = IR(
        design_name="up_down_counter",
        hdl_source="counter.vhd",
        hdl_language="vhdl",
        ports=[],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )
    ir.register_map = parse_regmap(COUNTER_REGMAP)
    return ir


def _make_ir_without_regmap() -> IR:
    """Return a minimal IR with register_map=None."""
    return IR(
        design_name="up_down_counter",
        hdl_source="counter.vhd",
        hdl_language="vhdl",
        ports=[],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )


# ---------------------------------------------------------------------------
# Core generation tests
# ---------------------------------------------------------------------------

def test_ral_gen_returns_three_artifacts() -> None:
    """generate_ral returns exactly three artifacts."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    assert len(artifacts) == 3


def test_ral_gen_returns_empty_without_regmap() -> None:
    """generate_ral returns empty list when ir.register_map is None."""
    ir = _make_ir_without_regmap()
    assert generate_ral(ir) == []


def test_ral_gen_reg_block_contains_uvm_reg_block() -> None:
    """reg_block.sv content contains 'extends uvm_reg_block'."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    block = next(a for a in artifacts if a.filename.endswith("_reg_block.sv"))
    assert "extends uvm_reg_block" in block.content


def test_ral_gen_reg_block_contains_all_registers() -> None:
    """reg_block.sv contains lowercase register names ctrl, status, count."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    block = next(a for a in artifacts if a.filename.endswith("_reg_block.sv"))
    assert "ctrl" in block.content
    assert "status" in block.content
    assert "count" in block.content


def test_ral_gen_reg_block_contains_create_map() -> None:
    """reg_block.sv contains 'create_map'."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    block = next(a for a in artifacts if a.filename.endswith("_reg_block.sv"))
    assert "create_map" in block.content


def test_ral_gen_reg_block_contains_add_reg() -> None:
    """reg_block.sv contains 'add_reg'."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    block = next(a for a in artifacts if a.filename.endswith("_reg_block.sv"))
    assert "add_reg" in block.content


def test_ral_gen_reg_pkg_contains_package() -> None:
    """reg_pkg.sv content contains 'package' and 'import uvm_pkg'."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    pkg = next(a for a in artifacts if a.filename.endswith("_reg_pkg.sv"))
    assert "package" in pkg.content
    assert "import uvm_pkg" in pkg.content


def test_ral_gen_reg_seq_contains_reset_seq() -> None:
    """reg_seq.sv contains 'uvm_reg_hw_reset_seq'."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    seq = next(a for a in artifacts if a.filename.endswith("_reg_seq.sv"))
    assert "uvm_reg_hw_reset_seq" in seq.content


def test_ral_gen_reg_seq_contains_rw_seq() -> None:
    """reg_seq.sv contains 'uvm_reg_sequence'."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    seq = next(a for a in artifacts if a.filename.endswith("_reg_seq.sv"))
    assert "uvm_reg_sequence" in seq.content


def test_ral_gen_pss_action_seq_generated() -> None:
    """reg_seq.sv contains ctrl_enable_seq from CTRL.ENABLE pss_action."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    seq = next(a for a in artifacts if a.filename.endswith("_reg_seq.sv"))
    assert "ctrl_enable_seq" in seq.content


def test_ral_gen_reserved_fields_excluded() -> None:
    """reg_block.sv does NOT contain 'reserved.configure' (reserved fields are skipped)."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    block = next(a for a in artifacts if a.filename.endswith("_reg_block.sv"))
    assert "reserved.configure" not in block.content


def test_ral_gen_context_endianness_conversion() -> None:
    """_build_ral_context converts 'Little' → 'LITTLE' for UVM_LITTLE_ENDIAN."""
    ir = _make_ir_with_regmap()
    ctx = _build_ral_context(ir)
    assert ctx["endianness"] == "LITTLE"
