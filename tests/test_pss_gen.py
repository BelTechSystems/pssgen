# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""Unit tests for the PSS generation agent and PSS checker path."""

from __future__ import annotations

from agents.pss_gen import generate_pss
from agents.structure_gen import Artifact
from checkers.verifier import _tier1_pss_structural
from ir import IR
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
