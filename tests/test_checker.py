"""Unit tests for the verifier checker (tier 1, no simulator required)."""
import pytest
from agents.structure_gen import Artifact
from agents.structure_gen import generate
from checkers.verifier import check, _tier1_ral_structural
from parser.verilog import parse


def _make_artifacts(driver_extra="", monitor_extra=""):
    return [
        Artifact("mydesign_if.sv",     "interface mydesign_if(input logic clk);\nendinterface"),
        Artifact("mydesign_driver.sv",  f"`uvm_component_utils(mydesign_driver)\nbuild_phase run_phase{driver_extra}"),
        Artifact("mydesign_monitor.sv", f"`uvm_component_utils(mydesign_monitor)\nwrite({monitor_extra}"),
        Artifact("mydesign_seqr.sv",    "`uvm_component_utils(mydesign_sequencer)"),
        Artifact("mydesign_agent.sv",   "`uvm_component_utils(mydesign_agent)\nbuild_phase"),
        Artifact("mydesign_test.sv",    "`uvm_component_utils(mydesign_test)"),
        Artifact("build.tcl",           "create_project mydesign_tb"),
    ]


def test_checker_tier1_pass():
    result = check(_make_artifacts(), sim_target="vivado")
    assert result.passed is True


def test_checker_tier1_missing_run_phase():
    artifacts = _make_artifacts()
    # Remove run_phase from driver
    for a in artifacts:
        if a.filename.endswith("_driver.sv"):
            a.content = a.content.replace("run_phase", "")
    result = check(artifacts, sim_target="vivado")
    assert result.passed is False
    assert result.tier == 1
    assert "run_phase" in result.reason


def test_checker_tier1_missing_write():
    artifacts = _make_artifacts()
    for a in artifacts:
        if a.filename.endswith("_monitor.sv"):
            a.content = a.content.replace("write(", "")
    result = check(artifacts, sim_target="vivado")
    assert result.passed is False
    assert result.tier == 1
    assert "write(" in result.reason


def test_checker_tier3_missing_build_script():
    artifacts = [a for a in _make_artifacts() if "build" not in a.filename]
    result = check(artifacts, sim_target="vivado")
    assert result.passed is False
    assert result.tier == 3


def test_template_only_output_passes_tier1(tmp_path):
    """Template-only output for counter.v must pass the
    tier-1 structural checker without any LLM call.

    This is the primary CI-safe smoke test for the
    generation pipeline. It must never require
    ANTHROPIC_API_KEY.
    """
    ir = parse("tests/fixtures/counter.v", top_module=None)
    ir.output_dir = str(tmp_path)
    ir.emission_target = "vivado"

    artifacts = generate(ir, no_llm=True)
    result = check(artifacts, "vivado")

    assert result.passed is True


# ── RAL tier-1 checker tests ──────────────────────────────────────────────

def test_checker_passes_valid_reg_block() -> None:
    """Minimal valid reg_block.sv passes _tier1_ral_structural."""
    content = (
        "class mydesign_ctrl_reg extends uvm_reg;\n"
        "endclass\n"
        "class mydesign_reg_block extends uvm_reg_block;\n"
        "  function void build();\n"
        "    reg_map = create_map(...);\n"
        "    reg_map.add_reg(.rg(ctrl), .offset(0));\n"
        "  endfunction\n"
        "endclass\n"
    )
    a = Artifact("mydesign_reg_block.sv", content)
    result = _tier1_ral_structural(a, "mydesign")
    assert result.passed is True


def test_checker_fails_missing_create_map() -> None:
    """reg_block.sv without 'create_map' fails tier-1 with descriptive reason."""
    content = (
        "class mydesign_ctrl_reg extends uvm_reg;\nendclass\n"
        "class mydesign_reg_block extends uvm_reg_block;\n"
        "  function void build();\n"
        "    reg_map.add_reg(.rg(ctrl), .offset(0));\n"
        "  endfunction\n"
        "endclass\n"
    )
    a = Artifact("mydesign_reg_block.sv", content)
    result = _tier1_ral_structural(a, "mydesign")
    assert result.passed is False
    assert "create_map" in result.reason


def test_checker_passes_valid_reg_pkg() -> None:
    """Minimal valid reg_pkg.sv passes _tier1_ral_structural."""
    content = (
        "package mydesign_reg_pkg;\n"
        "  import uvm_pkg::*;\n"
        "  `include \"uvm_macros.svh\"\n"
        "  `include \"mydesign_reg_block.sv\"\n"
        "endpackage : mydesign_reg_pkg\n"
    )
    a = Artifact("mydesign_reg_pkg.sv", content)
    result = _tier1_ral_structural(a, "mydesign")
    assert result.passed is True


def test_checker_passes_valid_reg_seq() -> None:
    """Minimal valid reg_seq.sv passes _tier1_ral_structural."""
    content = (
        "class mydesign_reg_hw_reset_seq\n"
        "    extends uvm_reg_hw_reset_seq;\n"
        "endclass\n"
        "class mydesign_reg_rw_seq extends uvm_reg_sequence;\n"
        "endclass\n"
    )
    a = Artifact("mydesign_reg_seq.sv", content)
    result = _tier1_ral_structural(a, "mydesign")
    assert result.passed is True


def test_checker_passes_valid_reg_map() -> None:
    """Minimal valid _reg_map.sv passes _tier1_ral_structural check."""
    content = (
        "class my_project_reg_map extends uvm_reg_block;\n"
        "  uvm_reg_map sys_map;\n"
        "  virtual function void build();\n"
        "    sys_map = create_map(.name(\"sys_map\"), .base_addr(0), .n_bytes(4));\n"
        "    blocka.build();\n"
        "    sys_map.add_submap(blocka.reg_map, 32'h4000_0000);\n"
        "  endfunction\n"
        "endclass\n"
    )
    a = Artifact("my_project_reg_map.sv", content)
    result = _tier1_ral_structural(a, "my_project")
    assert result.passed is True
