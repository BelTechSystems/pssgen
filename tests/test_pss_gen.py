# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""Unit tests for the PSS generation agent and PSS checker path."""

from __future__ import annotations

from unittest.mock import patch

from agents.pss_gen import generate_pss
from agents.structure_gen import Artifact
from checkers.verifier import _tier1_pss_structural
from checkers.verifier import CheckResult
from ir import IR
from orchestrator import JobSpec, run
from parser.verilog import parse


FIXTURE = "tests/fixtures/counter.v"


def _make_ir() -> IR:
    """Create canonical IR for PSS generation tests.

    Returns:
        Parsed IR for the counter fixture.
    """
    return parse(FIXTURE, top_module=None)


def test_pss_gen_template_only_contains_component() -> None:
    """Verify template-only PSS generation contains component declaration."""
    ir = _make_ir()
    out = generate_pss(ir, no_llm=True)
    assert "component" in out


def test_pss_gen_template_only_contains_action() -> None:
    """Verify template-only PSS generation contains action declarations."""
    ir = _make_ir()
    out = generate_pss(ir, no_llm=True)
    assert "action" in out


def test_pss_gen_template_only_contains_design_name() -> None:
    """Verify template-only PSS generation contains canonical design name."""
    ir = _make_ir()
    out = generate_pss(ir, no_llm=True)
    assert "up_down_counter" in out


def test_pss_gen_stores_in_ir() -> None:
    """Verify generate_pss stores generated source in ir.pss_model."""
    ir = _make_ir()
    out = generate_pss(ir, no_llm=True)
    assert ir.pss_model == out


def test_pss_checker_passes_valid_model() -> None:
    """Verify valid PSS model passes tier-1 PSS structural checks."""
    artifact = Artifact(
        filename="up_down_counter.pss",
        content="component up_down_counter { action a {} }",
    )
    result = _tier1_pss_structural(artifact, "up_down_counter")
    assert result.passed is True


def test_pss_checker_fails_missing_component() -> None:
    """Verify missing component keyword fails with descriptive tier-1 reason."""
    artifact = Artifact(
        filename="up_down_counter.pss",
        content="action a {}",
    )
    result = _tier1_pss_structural(artifact, "up_down_counter")
    assert result.passed is False
    assert result.tier == 1
    assert "missing 'component'" in result.reason


def test_pss_gen_with_intent_includes_comment() -> None:
    """Verify no-LLM PSS output preserves structured intent in comments."""
    ir = _make_ir()
    ir.pss_intent = "reset behavior:\n  Assert rst_n low for two cycles."

    out = generate_pss(ir, no_llm=True)

    assert "Verification intent (structured natural language):" in out
    assert "reset behavior:" in out


def test_pss_gen_without_intent_unchanged() -> None:
    """Verify no-LLM output remains IR-only when intent is not provided."""
    ir = _make_ir()
    ir.pss_intent = None

    out = generate_pss(ir, no_llm=True)

    assert "Verification intent" not in out


def test_intent_file_loads_into_ir(tmp_path) -> None:
    """Verify orchestrator loads intent file content into ir.pss_intent."""
    ir = _make_ir()
    intent_file = tmp_path / "counter.intent"
    intent_text = "reset behavior:\n  Hold reset for two cycles."
    intent_file.write_text(intent_text, encoding="utf-8")

    good_artifacts = [
        Artifact("x_if.sv", "interface x_if(input logic clk);\nendinterface"),
        Artifact("x_driver.sv", "`uvm_component_utils(x_driver)\nbuild_phase\nrun_phase"),
        Artifact("x_monitor.sv", "`uvm_component_utils(x_monitor)\nwrite("),
        Artifact("x_seqr.sv", "`uvm_component_utils(x_sequencer)"),
        Artifact("x_agent.sv", "`uvm_component_utils(x_agent)\nbuild_phase"),
        Artifact("x_test.sv", "`uvm_component_utils(x_test)"),
        Artifact("build.tcl", "create_project x_tb"),
    ]

    job = JobSpec(
        input_file=FIXTURE,
        intent_file=str(intent_file),
        top_module=None,
        out_dir=str(tmp_path / "out"),
        sim_target="vivado",
        max_retries=1,
        no_llm=True,
    )

    with patch("orchestrator.parse_source", return_value=ir), \
         patch("orchestrator.generate", return_value=good_artifacts), \
         patch(
             "orchestrator.generate_pss",
             return_value="component up_down_counter_comp { action a {} }",
         ), \
         patch("orchestrator.check", return_value=CheckResult(True, 3, "")), \
         patch("orchestrator.emit_vivado", return_value=[]):
        result = run(job)

    assert result.success is True
    assert ir.pss_intent == intent_text
