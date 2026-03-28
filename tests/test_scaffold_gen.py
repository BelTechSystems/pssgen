# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""tests/test_scaffold_gen.py — Unit tests for agents/scaffold_gen.py.

Phase: v3a
Layer: 3 (agent)

Tests [GENERATED] marker presence, intent gap detection, human-contribution
notice, and req ID extraction from intent into the req scaffold.
"""
import os
import tempfile
import pytest
from ir import IR, Port
from parser.intent_parser import IntentParseResult
from agents.scaffold_gen import generate_intent_scaffold, generate_req_scaffold


def _make_ir() -> IR:
    """Build a minimal counter IR for testing."""
    return IR(
        design_name="up_down_counter",
        hdl_source="tests/fixtures/counter.vhd",
        hdl_language="vhdl",
        ports=[
            Port(name="clk",     direction="input",  width=1, role="clock"),
            Port(name="rst_n",   direction="input",  width=1, role="reset_n"),
            Port(name="enable",  direction="input",  width=1, role="control"),
            Port(name="up_down", direction="input",  width=1, role="control"),
            Port(name="count",   direction="output", width=8, role="data"),
        ],
        parameters={"WIDTH": "8"},
        emission_target="vivado",
        output_dir="./out",
    )


def _make_intent_result_no_coverage() -> IntentParseResult:
    """Build an intent result with no coverage of control/data ports."""
    return IntentParseResult(
        sections={"reset behavior": ["Apply reset low for 2 cycles."]},
        req_ids=[],
        req_schemes=[],
        waivers=[],
    )


def _make_intent_result_with_ids() -> IntentParseResult:
    """Build an intent result with requirement IDs."""
    return IntentParseResult(
        sections={"reset behavior": ["Apply reset. [SYS-REQ-001]"]},
        req_ids=["SYS-REQ-001", "FUNC-REQ-002"],
        req_schemes=["SYS-REQ", "FUNC-REQ"],
        waivers=[],
    )


def test_scaffold_gen_intent_contains_generated_markers() -> None:
    """[GENERATED] markers are present in the intent scaffold output."""
    ir = _make_ir()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "counter_generated.intent")
        generate_intent_scaffold(ir, None, out_path)
        content = open(out_path, encoding="utf-8").read()
        assert "[GENERATED]" in content


def test_scaffold_gen_intent_contains_gap_section() -> None:
    """Uncovered control/data ports appear in the gaps section of the intent scaffold."""
    ir = _make_ir()
    # Intent result that mentions reset but not enable, up_down, or count
    intent_result = _make_intent_result_no_coverage()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "counter_generated.intent")
        generate_intent_scaffold(ir, intent_result, out_path)
        content = open(out_path, encoding="utf-8").read()
        # enable, up_down, count are not mentioned in intent sections
        assert "intent gaps" in content.lower()
        assert "enable" in content or "up_down" in content or "count" in content


def test_scaffold_gen_req_contains_human_notice() -> None:
    """The never-overwrite human notice is present in the req scaffold."""
    ir = _make_ir()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "counter_generated.req")
        generate_req_scaffold(ir, None, out_path)
        content = open(out_path, encoding="utf-8").read()
        assert "This file will never be overwritten by pssgen" in content


def test_scaffold_gen_req_extracts_ids_from_intent() -> None:
    """Requirement IDs from intent appear as entries in the req scaffold."""
    ir = _make_ir()
    intent_result = _make_intent_result_with_ids()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "counter_generated.req")
        generate_req_scaffold(ir, intent_result, out_path)
        content = open(out_path, encoding="utf-8").read()
        assert "SYS-REQ-001" in content
        assert "FUNC-REQ-002" in content
