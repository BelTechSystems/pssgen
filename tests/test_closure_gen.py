# ===========================================================
# FILE:         tests/test_closure_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/closure_gen.py. Verifies that closure scripts
#   are created with the correct naming convention, contain the expected
#   simulator commands, and include the pass number in the filename.
#
# LAYER:        Tests
# PHASE:        v3c-b
#
# HISTORY:
#   v3c-b  2026-03-29  SB  Initial implementation; 6 closure gen tests
#
# ===========================================================
"""Unit tests for the coverage closure script generator."""

from __future__ import annotations

import os

import pytest

from agents.closure_gen import generate_closure_script
from agents.gap_agent import GapReport
from ir import IR, Port


def _make_ir(design_name: str = "test_design") -> IR:
    """Create a minimal IR for closure gen tests."""
    return IR(
        design_name=design_name,
        hdl_source="test.vhd",
        hdl_language="vhdl",
        ports=[Port("clk", "input", 1, "clock")],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )


def _make_gap_report(n_errors: int = 1, n_warnings: int = 2) -> GapReport:
    """Create a minimal GapReport with the given error/warning counts."""
    report = GapReport(design_name="test_design")
    for i in range(n_errors):
        report.errors.append({"req_id": f"REQ-{i:03d}", "message": "test"})
    for i in range(n_warnings):
        report.warnings.append({"label": f"cg_warn_{i}", "message": "test"})
    return report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_closure_gen_vivado_creates_sh_file(tmp_path) -> None:
    """generate_closure_script() with vivado target creates run_closure_pass_1.sh."""
    ir = _make_ir()
    gap_report = _make_gap_report()

    script_path = generate_closure_script(ir, "vivado", 1, gap_report, str(tmp_path))

    assert os.path.isfile(script_path)
    assert os.path.basename(script_path) == "run_closure_pass_1.sh"


def test_closure_gen_script_contains_vivado_command(tmp_path) -> None:
    """Vivado closure script contains 'vivado -mode batch'."""
    ir = _make_ir()
    gap_report = _make_gap_report()

    script_path = generate_closure_script(ir, "vivado", 1, gap_report, str(tmp_path))
    content = open(script_path, encoding="utf-8").read()

    assert "vivado -mode batch" in content


def test_closure_gen_questa_creates_sh_file(tmp_path) -> None:
    """questa target creates run_closure_pass_1.sh."""
    ir = _make_ir()
    gap_report = _make_gap_report()

    script_path = generate_closure_script(ir, "questa", 1, gap_report, str(tmp_path))

    assert os.path.isfile(script_path)
    assert os.path.basename(script_path) == "run_closure_pass_1.sh"


def test_closure_gen_icarus_creates_sh_file(tmp_path) -> None:
    """icarus target creates run_closure_pass_1.sh with iverilog reference."""
    ir = _make_ir()
    gap_report = _make_gap_report()

    script_path = generate_closure_script(ir, "icarus", 1, gap_report, str(tmp_path))
    content = open(script_path, encoding="utf-8").read()

    assert os.path.isfile(script_path)
    assert "iverilog" in content


def test_closure_gen_none_creates_sh_file(tmp_path) -> None:
    """none target creates a script with 'No simulator' message."""
    ir = _make_ir()
    gap_report = _make_gap_report()

    script_path = generate_closure_script(ir, "none", 1, gap_report, str(tmp_path))
    content = open(script_path, encoding="utf-8").read()

    assert os.path.isfile(script_path)
    assert "No simulator" in content


def test_closure_gen_pass_number_in_filename(tmp_path) -> None:
    """pass_number=3 creates run_closure_pass_3.sh."""
    ir = _make_ir()
    gap_report = _make_gap_report()

    script_path = generate_closure_script(ir, "vivado", 3, gap_report, str(tmp_path))

    assert os.path.basename(script_path) == "run_closure_pass_3.sh"
