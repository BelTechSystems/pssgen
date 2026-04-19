# ===========================================================
# FILE:         tests/test_ral_session2.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for RAL Session 2 — verifies that scaffold_gen.py generates
#   RAL-wired env.sv (balu_reg_model, adapter, predictor, config_db),
#   axi4_lite_if-based tb_top.sv, and the expanded Session 2 build.tcl.
#   Also verifies the ral_enabled flag produces the expected variant.
#
# LAYER:        4 — checkers / tests
# PHASE:        D-034 / RAL Session 2
#
# HISTORY:
#   RAL-S2  2026-04-18  SB  Initial implementation
#
# ===========================================================
import os
import pytest
from ir import IR, Port
from agents.scaffold_gen import _gen_env, _gen_tb_top, _gen_build_tcl

SESSION2_TB      = "output/balu_ral_session2/tb"
SESSION2_SCRIPTS = f"{SESSION2_TB}/scripts/vivado"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read(rel_path: str) -> str:
    with open(rel_path, encoding="utf-8") as fh:
        return fh.read()


def _minimal_ir(hdl_language: str = "systemverilog") -> IR:
    """Return a minimal IR with one clock port for function-level tests."""
    return IR(
        design_name="test_dut",
        hdl_source="test_dut.sv",
        hdl_language=hdl_language,
        ports=[Port(name="clk", direction="input", width=1, role="clock")],
        parameters={},
        emission_target="vivado",
        output_dir="out",
    )


# ── Tests 1–4: generated env.sv ───────────────────────────────────────────────

def test_generated_env_contains_balu_reg_model():
    content = _read(f"{SESSION2_TB}/buffered_axi_lite_uart_env.sv")
    assert "balu_reg_model" in content


def test_generated_env_contains_axi4_lite_reg_adapter():
    content = _read(f"{SESSION2_TB}/buffered_axi_lite_uart_env.sv")
    assert "axi4_lite_reg_adapter" in content


def test_generated_env_contains_axi4_lite_predictor():
    content = _read(f"{SESSION2_TB}/buffered_axi_lite_uart_env.sv")
    assert "axi4_lite_predictor" in content


def test_generated_env_contains_uvm_config_db_reg_model():
    content = _read(f"{SESSION2_TB}/buffered_axi_lite_uart_env.sv")
    assert "uvm_config_db" in content
    assert "reg_model" in content


# ── Tests 5–7: generated tb_top.sv ───────────────────────────────────────────

def test_generated_tb_top_contains_axi4_lite_if():
    content = _read(f"{SESSION2_TB}/tb_top.sv")
    assert "axi4_lite_if" in content


def test_generated_tb_top_contains_uart_loopback():
    content = _read(f"{SESSION2_TB}/tb_top.sv")
    assert "uart_loopback" in content


def test_generated_tb_top_contains_uvm_config_db_vif():
    content = _read(f"{SESSION2_TB}/tb_top.sv")
    assert "uvm_config_db" in content
    assert "vif" in content


# ── Tests 8–9: generated build.tcl ───────────────────────────────────────────

def test_generated_build_tcl_contains_SIM_LIB():
    content = _read(f"{SESSION2_SCRIPTS}/build.tcl")
    assert "SIM_LIB" in content


def test_generated_build_tcl_contains_xvhdl_note():
    content = _read(f"{SESSION2_SCRIPTS}/build.tcl")
    assert "xvhdl" in content


# ── Tests 10–11: scaffold_gen ral_enabled flag ────────────────────────────────

def test_gen_env_ral_enabled_true_contains_balu_reg_model():
    content = _gen_env("test_dut", ral_enabled=True)
    assert "balu_reg_model" in content
    assert "axi4_lite_reg_adapter" in content
    assert "axi4_lite_predictor" in content
    assert "uvm_config_db" in content


def test_gen_env_ral_enabled_false_is_stub_without_ral():
    content = _gen_env("test_dut", ral_enabled=False)
    assert "balu_reg_model" not in content
    assert "axi4_lite_reg_adapter" not in content
    assert "axi4_lite_predictor" not in content
