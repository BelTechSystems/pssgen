# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""Unit tests for the PSS generation agent and PSS checker path."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

from agents.pss_gen import generate_pss, _build_coverage_labels
from agents.structure_gen import Artifact
from checkers.verifier import _tier1_pss_structural
from checkers.verifier import CheckResult
from ir import IR, Port
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


# ---------------------------------------------------------------------------
# v3b: coverage label tests
# ---------------------------------------------------------------------------

@dataclass
class _FakeIntentResult:
    """Minimal stand-in for IntentParseResult in coverage label tests."""
    sections: dict = field(default_factory=dict)
    req_ids: list = field(default_factory=list)
    req_schemes: list = field(default_factory=list)
    waivers: list = field(default_factory=list)


def test_coverage_labels_tier1_req_id() -> None:
    """Req IDs in intent_result produce Tier-1 coverage labels."""
    ir = _make_ir()
    intent = _FakeIntentResult(req_ids=["FUNC-REQ-113"])

    labels = _build_coverage_labels(ir, intent)

    tier1 = [lbl for lbl in labels if lbl["source"] == "requirement"]
    assert len(tier1) >= 1
    assert any(lbl["label"] == "cg_FUNC_REQ_113" for lbl in tier1)


def test_coverage_labels_tier2_intent_section() -> None:
    """Intent section headings without req IDs produce Tier-2 coverage labels."""
    ir = _make_ir()
    intent = _FakeIntentResult(
        sections={"coverage goals": ["some coverage text"]},
        req_ids=[],
    )

    labels = _build_coverage_labels(ir, intent)

    tier2 = [lbl for lbl in labels if lbl["source"] == "intent"]
    assert len(tier2) >= 1
    assert any(lbl["label"].startswith("cg_coverage_goals") for lbl in tier2)


def test_coverage_labels_tier3_inferred() -> None:
    """Data output ports with no intent_result produce Tier-3 inferred labels."""
    # Use only a data output port and a clock; no intent
    ir = IR(
        design_name="simple",
        hdl_source="simple.v",
        hdl_language="verilog",
        ports=[
            Port("clk", "input", 1, "clock"),
            Port("count", "output", 8, "data"),
        ],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )

    labels = _build_coverage_labels(ir, None)

    tier3 = [lbl for lbl in labels if lbl["source"] == "inferred"]
    assert len(tier3) >= 1
    assert any("count" in lbl["label"] for lbl in tier3)


def test_coverage_labels_waived_excluded_from_active() -> None:
    """Req IDs present in intent waivers produce waived=True label entries."""
    ir = _make_ir()
    intent = _FakeIntentResult(
        req_ids=["FUNC-REQ-113"],
        waivers=[{
            "item": "some item",
            "reason": "Cannot test pre-silicon.",
            "req_ids": ["FUNC-REQ-113"],
        }],
    )

    labels = _build_coverage_labels(ir, intent)

    func_req_labels = [lbl for lbl in labels if lbl.get("req_id") == "FUNC-REQ-113"]
    assert len(func_req_labels) == 1
    assert func_req_labels[0]["waived"] is True


def test_pss_template_uses_named_covergroups() -> None:
    """Template output contains named covergroup cg_ entries, not cg_default."""
    ir = parse(FIXTURE, top_module=None)
    # Provide intent with sections to ensure Tier-2 labels exist
    from parser.intent_parser import parse_intent
    intent = parse_intent("tests/fixtures/counter.intent")
    out = generate_pss(ir, no_llm=True, intent_result=intent)

    assert "covergroup cg_" in out
    # The named covergroups should appear; cg_default is the fallback only
    assert "cg_default" not in out
