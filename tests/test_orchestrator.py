"""Integration test: orchestrator retry loop fires on checker failure."""
import pytest
from unittest.mock import patch, MagicMock
from orchestrator import run, JobSpec
from agents.structure_gen import Artifact
from checkers.verifier import CheckResult


GOOD_ARTIFACTS = [
    Artifact("x_if.sv",      "interface x_if(input logic clk);\nendinterface"),
    Artifact("x_driver.sv",  "`uvm_component_utils(x_driver)\nbuild_phase run_phase"),
    Artifact("x_monitor.sv", "`uvm_component_utils(x_monitor)\nwrite("),
    Artifact("x_seqr.sv",    "`uvm_component_utils(x_sequencer)"),
    Artifact("x_agent.sv",   "`uvm_component_utils(x_agent)\nbuild_phase"),
    Artifact("x_test.sv",    "`uvm_component_utils(x_test)"),
    Artifact("build.tcl",    "create_project x_tb"),
]


def test_orchestrator_retry_fires(tmp_path):
    job = JobSpec(
        input_file="tests/fixtures/counter.v",
        top_module=None,
        out_dir=str(tmp_path),
        sim_target="vivado",
        max_retries=3,
    )
    call_count = {"n": 0}

    def mock_generate(ir, fail_reason=None, no_llm=False):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First attempt: return bad artifact (missing run_phase in driver)
            bad = list(GOOD_ARTIFACTS)
            bad[1] = Artifact("x_driver.sv", "`uvm_component_utils(x_driver)\nbuild_phase")
            return bad
        return GOOD_ARTIFACTS

    with patch("orchestrator.generate", side_effect=mock_generate), \
         patch("orchestrator.emit_vivado", return_value=[]):
        result = run(job)

    assert result.attempts == 2
    assert result.success is True
    assert call_count["n"] == 2
