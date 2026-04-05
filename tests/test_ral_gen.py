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
#   v4c   2026-04-05  SB  Added 5 system-assembly tests (multi-block reg_map.sv)
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
from agents.ral_gen import generate_ral, _build_ral_context, _build_system_context
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


# ---------------------------------------------------------------------------
# System assembly tests (v4c)
# ---------------------------------------------------------------------------

def _make_ir_with_two_blocks() -> IR:
    """Return IR with a two-block register_map for system assembly testing."""
    ir = IR(
        design_name="dual_block",
        hdl_source="dual.vhd",
        hdl_language="vhdl",
        ports=[],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )
    ir.register_map = {
        "globals": {
            "project_name": "dual_block_project",
            "base_address": "0x0",
            "data_width_bits": "32",
            "endianness": "Little",
        },
        "blocks": [
            {"block_name": "BLOCKA", "base_address": "0x4000_0000",
             "data_width_bits": "32", "reset_domain": "", "clock_domain": "",
             "description": ""},
            {"block_name": "BLOCKB", "base_address": "0x4001_0000",
             "data_width_bits": "32", "reset_domain": "", "clock_domain": "",
             "description": ""},
        ],
        "registers": [
            {"block": "BLOCKA", "name": "REG0", "description": "",
             "offset": "0x00", "width": 32, "fields": [
                 {"field_name": "F0", "bit_offset": 0, "bit_width": 8,
                  "access": "RW", "reset_value": "0x0", "volatile": False,
                  "hw_access": "NA", "sw_access": "RW", "field_kind": "normal",
                  "enum_ref": None, "uvm_has_coverage": False, "req_id": None,
                  "pss_action": None, "hdl_path": None, "description": "",
                  "name": "F0"},
             ]},
            {"block": "BLOCKB", "name": "REG1", "description": "",
             "offset": "0x00", "width": 32, "fields": [
                 {"field_name": "G0", "bit_offset": 0, "bit_width": 8,
                  "access": "RW", "reset_value": "0x0", "volatile": False,
                  "hw_access": "NA", "sw_access": "RW", "field_kind": "normal",
                  "enum_ref": None, "uvm_has_coverage": False, "req_id": None,
                  "pss_action": None, "hdl_path": None, "description": "",
                  "name": "G0"},
             ]},
        ],
        "enums": {},
    }
    return ir


def test_ral_gen_system_assembly_for_multi_block() -> None:
    """generate_ral returns 7 artifacts (3 per block + reg_map.sv) for 2 blocks."""
    ir = _make_ir_with_two_blocks()
    artifacts = generate_ral(ir)
    # 2 blocks × 3 templates + 1 system reg_map.sv = 7
    assert len(artifacts) == 7
    reg_map_files = [a for a in artifacts if a.filename.endswith("_reg_map.sv")]
    assert len(reg_map_files) == 1


def test_ral_gen_no_system_assembly_single_block() -> None:
    """generate_ral returns exactly 3 artifacts for a single-block register_map."""
    ir = _make_ir_with_regmap()
    artifacts = generate_ral(ir)
    assert len(artifacts) == 3


def test_ral_gen_reg_map_contains_add_submap() -> None:
    """Multi-block → _reg_map.sv content contains 'add_submap'."""
    ir = _make_ir_with_two_blocks()
    artifacts = generate_ral(ir)
    reg_map = next(a for a in artifacts if a.filename.endswith("_reg_map.sv"))
    assert "add_submap" in reg_map.content


def test_ral_gen_reg_map_contains_sys_map() -> None:
    """Multi-block → _reg_map.sv content contains 'sys_map'."""
    ir = _make_ir_with_two_blocks()
    artifacts = generate_ral(ir)
    reg_map = next(a for a in artifacts if a.filename.endswith("_reg_map.sv"))
    assert "sys_map" in reg_map.content


def test_ral_gen_reg_map_project_name_in_class() -> None:
    """project_name appears in class declaration in _reg_map.sv."""
    ir = _make_ir_with_two_blocks()
    artifacts = generate_ral(ir)
    reg_map = next(a for a in artifacts if a.filename.endswith("_reg_map.sv"))
    assert "dual_block_project_reg_map" in reg_map.content
