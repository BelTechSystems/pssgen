# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""tests/test_emitter_questa.py — Unit tests for the Questa artifact emitter.

Phase: v2c
Layer: 5 (emitters)

Verifies that emitters/questa.py writes the correct files, produces a valid
Makefile with Questa-specific content, and handles .pss artifacts correctly.
"""
import os

from agents.structure_gen import Artifact
from emitters.questa import emit
from ir import IR, Port


def _make_ir() -> IR:
    """Build a minimal IR for Questa emitter tests.

    Returns:
        Minimal IR instance for up_down_counter.
    """
    ir = IR(
        design_name="up_down_counter",
        hdl_source="tests/fixtures/counter.vhd",
        hdl_language="vhdl",
        ports=[Port("clk", "input", 1, "clock")],
        parameters={},
        emission_target="questa",
        output_dir="",
    )
    ir.pss_model = "component up_down_counter { action a {} }"
    return ir


def _make_artifacts() -> list[Artifact]:
    """Build a representative artifact list matching orchestrator output.

    Returns:
        List of Artifact instances covering .sv, .pss, and .tcl types.
    """
    return [
        Artifact("up_down_counter_if.sv",      "interface up_down_counter_if;\nendinterface"),
        Artifact("up_down_counter_driver.sv",  "`uvm_component_utils(up_down_counter_driver)"),
        Artifact("up_down_counter_monitor.sv", "`uvm_component_utils(up_down_counter_monitor)"),
        Artifact("up_down_counter_seqr.sv",    "`uvm_component_utils(up_down_counter_seqr)"),
        Artifact("up_down_counter_agent.sv",   "`uvm_component_utils(up_down_counter_agent)"),
        Artifact("up_down_counter_test.sv",    "`uvm_component_utils(up_down_counter_test)"),
        Artifact("build.tcl",                  "create_project up_down_counter_tb"),
        Artifact("up_down_counter.pss",        "component up_down_counter { action a {} }"),
    ]


def test_questa_emitter_writes_sv_files(tmp_path) -> None:
    """emit() writes all .sv artifacts to out_dir."""
    ir = _make_ir()
    artifacts = _make_artifacts()
    emit(ir, artifacts, str(tmp_path))
    sv_written = [f for f in os.listdir(str(tmp_path)) if f.endswith(".sv")]
    sv_expected = [a.filename for a in artifacts if a.filename.endswith(".sv")]
    assert sorted(sv_written) == sorted(sv_expected)


def test_questa_emitter_writes_makefile(tmp_path) -> None:
    """emit() writes a file named exactly Makefile."""
    ir = _make_ir()
    emit(ir, _make_artifacts(), str(tmp_path))
    assert os.path.isfile(os.path.join(str(tmp_path), "Makefile"))


def test_questa_emitter_makefile_contains_vsim(tmp_path) -> None:
    """Makefile content references vsim for simulation."""
    ir = _make_ir()
    emit(ir, _make_artifacts(), str(tmp_path))
    content = open(os.path.join(str(tmp_path), "Makefile")).read()
    assert "vsim" in content


def test_questa_emitter_makefile_contains_vlog(tmp_path) -> None:
    """Makefile content references vlog for compilation."""
    ir = _make_ir()
    emit(ir, _make_artifacts(), str(tmp_path))
    content = open(os.path.join(str(tmp_path), "Makefile")).read()
    assert "vlog" in content


def test_questa_emitter_makefile_contains_design_name(tmp_path) -> None:
    """Makefile content contains ir.design_name."""
    ir = _make_ir()
    emit(ir, _make_artifacts(), str(tmp_path))
    content = open(os.path.join(str(tmp_path), "Makefile")).read()
    assert ir.design_name in content


def test_questa_emitter_writes_pss_file(tmp_path) -> None:
    """emit() writes the .pss artifact alongside the .sv files."""
    ir = _make_ir()
    emit(ir, _make_artifacts(), str(tmp_path))
    assert os.path.isfile(os.path.join(str(tmp_path), "up_down_counter.pss"))


def test_questa_emitter_returns_all_paths(tmp_path) -> None:
    """Return value includes paths for all written files."""
    ir = _make_ir()
    written = emit(ir, _make_artifacts(), str(tmp_path))
    written_names = {os.path.basename(p) for p in written}
    # Expect 6 .sv files + 1 .pss + Makefile = 8 files; build.tcl excluded
    assert "Makefile" in written_names
    assert "up_down_counter.pss" in written_names
    assert all(p.endswith(".sv") or p.endswith(".pss") or p == "Makefile"
               for p in written_names)
