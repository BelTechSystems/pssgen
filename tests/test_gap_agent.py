# ===========================================================
# FILE:         tests/test_gap_agent.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/gap_agent.py. Verifies bidirectional gap analysis,
#   error/warning/waiver classification, report writing, and console summary
#   formatting. All tests run without LLM or file system fixtures beyond
#   tmp_path.
#
# LAYER:        Tests
# PHASE:        v3b
#
# HISTORY:
#   v3b   2026-03-28  SB  Initial implementation; 9 gap agent tests
#
# ===========================================================
"""Unit tests for the gap analysis agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pytest

from agents.gap_agent import analyse_gaps, write_gap_report, format_console_summary, GapReport
from ir import IR, Port


# ---------------------------------------------------------------------------
# Minimal stub types — mirrors ReqParseResult / IntentParseResult without
# importing parsers (avoids cross-module coupling in tests).
# ---------------------------------------------------------------------------

@dataclass
class _FakeReqResult:
    requirements: dict = field(default_factory=dict)
    waivers: list = field(default_factory=list)


@dataclass
class _FakeIntentResult:
    sections: dict = field(default_factory=dict)
    req_ids: list = field(default_factory=list)
    req_schemes: list = field(default_factory=list)
    waivers: list = field(default_factory=list)


def _make_ir(design_name: str = "test_design") -> IR:
    """Create a minimal IR for gap agent tests."""
    return IR(
        design_name=design_name,
        hdl_source="test.v",
        hdl_language="verilog",
        ports=[
            Port("clk", "input", 1, "clock"),
            Port("rst_n", "input", 1, "reset_n"),
            Port("count", "output", 8, "data"),
        ],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_gap_agent_direction_a_error() -> None:
    """Requirements not covered by any PSS label generate Direction-A errors."""
    ir = _make_ir()
    req_result = _FakeReqResult(
        requirements={
            "SYS-REQ-001": {
                "statement": "Counter shall support active-low reset.",
                "verification": ["simulation"],
                "waived": False,
                "waiver_reason": "",
            }
        }
    )
    # No coverage labels — SYS-REQ-001 has no matching label
    coverage_labels: list[dict] = []

    report = analyse_gaps(ir, None, req_result, coverage_labels)

    assert len(report.errors) == 1
    assert report.errors[0]["req_id"] == "SYS-REQ-001"


def test_gap_agent_direction_b_warning() -> None:
    """PSS labels from intent with no req_id generate Direction-B warnings."""
    ir = _make_ir()
    coverage_labels = [
        {
            "label": "cg_coverage_goals_01",
            "display": "coverage goals",
            "source": "intent",
            "req_id": None,
            "waived": False,
            "waiver_reason": None,
        }
    ]

    report = analyse_gaps(ir, _FakeIntentResult(), None, coverage_labels)

    assert len(report.warnings) == 1
    assert "cg_coverage_goals_01" in report.warnings[0]["message"]


def test_gap_agent_waived_not_counted() -> None:
    """Waived requirements are not counted as errors; they appear in waivers."""
    ir = _make_ir()
    req_result = _FakeReqResult(
        requirements={
            "SYS-REQ-001": {
                "statement": "Waived requirement.",
                "verification": [],
                "waived": True,
                "waiver_reason": "Cannot verify pre-silicon.",
            }
        },
        waivers=["SYS-REQ-001"],
    )
    coverage_labels: list[dict] = []

    report = analyse_gaps(ir, None, req_result, coverage_labels)

    assert len(report.errors) == 0
    assert len(report.waivers) == 1
    assert report.waivers[0]["req_id"] == "SYS-REQ-001"


def test_gap_agent_matched_req_not_flagged() -> None:
    """Requirements with a matching PSS coverage label are not errors."""
    ir = _make_ir()
    req_result = _FakeReqResult(
        requirements={
            "SYS-REQ-001": {
                "statement": "Counter shall support active-low reset.",
                "verification": ["simulation"],
                "waived": False,
                "waiver_reason": "",
            }
        }
    )
    coverage_labels = [
        {
            "label": "cg_SYS_REQ_001",
            "display": "SYS-REQ-001",
            "source": "requirement",
            "req_id": "SYS-REQ-001",
            "waived": False,
            "waiver_reason": None,
        }
    ]

    report = analyse_gaps(ir, None, req_result, coverage_labels)

    assert len(report.errors) == 0


def test_gap_agent_no_req_file_no_errors() -> None:
    """When req_result is None, no Direction-A errors are generated."""
    ir = _make_ir()
    coverage_labels = [
        {
            "label": "cg_coverage_goals_01",
            "display": "coverage goals",
            "source": "intent",
            "req_id": None,
            "waived": False,
            "waiver_reason": None,
        }
    ]

    report = analyse_gaps(ir, _FakeIntentResult(), None, coverage_labels)

    assert len(report.errors) == 0


def test_gap_agent_no_intent_file_no_warnings() -> None:
    """Inferred-source coverage labels never generate Direction-B warnings."""
    ir = _make_ir()
    coverage_labels = [
        {
            "label": "cg_inferred_count_01",
            "display": "count",
            "source": "inferred",
            "req_id": None,
            "waived": False,
            "waiver_reason": None,
        }
    ]

    report = analyse_gaps(ir, None, None, coverage_labels)

    assert len(report.warnings) == 0


def test_gap_agent_write_report_creates_file(tmp_path) -> None:
    """write_gap_report creates the output file at the specified path."""
    ir = _make_ir()
    report = GapReport(design_name=ir.design_name)
    out_path = str(tmp_path / "test_gap_report.txt")

    result_path = write_gap_report(report, out_path)

    import os
    assert os.path.exists(result_path)
    assert result_path == out_path


def test_gap_agent_report_contains_error_section(tmp_path) -> None:
    """Written gap report contains an ERRORS section when errors are present."""
    ir = _make_ir()
    report = GapReport(design_name=ir.design_name)
    report.errors.append({
        "req_id": "SYS-REQ-001",
        "message": "Requirement 'SYS-REQ-001' has no corresponding PSS coverage label.",
        "statement": "Counter shall support active-low reset.",
    })
    out_path = str(tmp_path / "gap_report.txt")

    write_gap_report(report, out_path)

    content = open(out_path, encoding="utf-8").read()
    assert "ERRORS" in content
    assert "SYS-REQ-001" in content


def test_gap_agent_console_summary_format() -> None:
    """format_console_summary returns correct counts in the expected format."""
    report = GapReport(design_name="test_design")
    report.errors = [{"req_id": "A"}, {"req_id": "B"}]
    report.warnings = [{"label": "cg_x"}]

    summary = format_console_summary(report)

    assert "2 error" in summary
    assert "1 warning" in summary
