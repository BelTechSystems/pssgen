"""Unit tests for the verifier checker (tier 1, no simulator required)."""
import pytest
from agents.structure_gen import Artifact
from checkers.verifier import check


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
