# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""tests/test_emitter_c.py — Unit tests for the generic C test case emitter.

Phase: v2b
Layer: 5 (emitters)

Verifies that emitters/generic_c.py produces the expected C output file,
extracts PSS action names correctly, and handles the no-pss_model edge case.
"""
import os

import pytest

from agents.structure_gen import Artifact
from emitters.generic_c import emit
from ir import IR, Port


def _make_ir(pss_model: str | None = None) -> IR:
    """Build a minimal IR suitable for C emission tests.

    Args:
        pss_model: Optional PSS source string to store on the IR.

    Returns:
        Minimal IR instance for up_down_counter.
    """
    ir = IR(
        design_name="up_down_counter",
        hdl_source="tests/fixtures/counter.vhd",
        hdl_language="vhdl",
        ports=[
            Port("clk", "input", 1, "clock"),
            Port("rst_n", "input", 1, "reset_n"),
        ],
        parameters={},
        emission_target="generic",
        output_dir="",
    )
    ir.pss_model = pss_model
    return ir


_SAMPLE_PSS = """\
component up_down_counter {
    action Reset {}
    action CountUp {
        rand bit [7:0] count;
    }
}
"""


def test_c_emitter_produces_file(tmp_path) -> None:
    """emit() writes exactly one file ending in _pss_tests.c."""
    ir = _make_ir(pss_model=_SAMPLE_PSS)
    written = emit(ir, [], str(tmp_path))
    c_files = [p for p in written if p.endswith("_pss_tests.c")]
    assert len(c_files) == 1


def test_c_emitter_contains_run_all(tmp_path) -> None:
    """Output file contains the run_all_pss_tests harness function."""
    ir = _make_ir(pss_model=_SAMPLE_PSS)
    emit(ir, [], str(tmp_path))
    c_path = os.path.join(str(tmp_path), "up_down_counter_pss_tests.c")
    content = open(c_path).read()
    assert "run_all_pss_tests" in content


def test_c_emitter_extracts_actions_from_pss_model(tmp_path) -> None:
    """Given two named PSS actions, output contains test_<action>() for each."""
    ir = _make_ir(pss_model=_SAMPLE_PSS)
    emit(ir, [], str(tmp_path))
    c_path = os.path.join(str(tmp_path), "up_down_counter_pss_tests.c")
    content = open(c_path).read()
    assert "test_Reset()" in content
    assert "test_CountUp()" in content


def test_c_emitter_no_pss_model_writes_stub(tmp_path) -> None:
    """emit() still writes a file and does not raise when ir.pss_model is None."""
    ir = _make_ir(pss_model=None)
    written = emit(ir, [], str(tmp_path))
    c_files = [p for p in written if p.endswith("_pss_tests.c")]
    assert len(c_files) == 1
    content = open(c_files[0]).read()
    assert "run_all_pss_tests" in content


def test_c_emitter_correct_filename(tmp_path) -> None:
    """Output filename is <design_name>_pss_tests.c."""
    ir = _make_ir(pss_model=_SAMPLE_PSS)
    written = emit(ir, [], str(tmp_path))
    c_files = [os.path.basename(p) for p in written if p.endswith("_pss_tests.c")]
    assert c_files == ["up_down_counter_pss_tests.c"]
