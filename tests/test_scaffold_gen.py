# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""tests/test_scaffold_gen.py — Unit tests for agents/scaffold_gen.py.

Phase: v3a / D-032
Layer: 3 (agent)

Tests [GENERATED] marker presence, intent gap detection, human-contribution
notice, and req ID extraction from intent into the req scaffold.
Also tests generate_uvm_tb() for STD-003B file set generation.
"""
import os
import tempfile
import types
import pytest
from ir import IR, Port
from parser.intent_parser import IntentParseResult
from agents.scaffold_gen import generate_intent_scaffold, generate_req_scaffold, generate_uvm_tb


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


# ===========================================================================
# generate_uvm_tb() tests (D-032)
# ===========================================================================

def _make_uvm_ir(design_name: str = "test_dut") -> IR:
    """Build a minimal IR for UVM tb generation tests."""
    return IR(
        design_name=design_name,
        hdl_source=f"tests/fixtures/{design_name}.vhd",
        hdl_language="vhdl",
        ports=[
            Port(name="clk",    direction="input",  width=1, role="clock"),
            Port(name="rst_n",  direction="input",  width=1, role="reset_n"),
            Port(name="enable", direction="input",  width=1, role="control"),
            Port(name="addr",   direction="input",  width=8, role="data"),
            Port(name="data",   direction="output", width=8, role="data"),
        ],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )


def _make_cov_item(cov_id: str, name: str) -> object:
    """Build a minimal COV item namespace for stub tests."""
    item = types.SimpleNamespace()
    item.id = cov_id
    item.name = name
    item.linked_requirements = ["REQ-001"]
    item.stimulus_strategy = "Sweep all register values"
    item.boundary_values = "min=0, max=0xFFFFFFFF"
    return item


def _make_vplan_result_with_cov() -> object:
    """Build a minimal VplanParseResult-like object with two COV items."""
    vpr = types.SimpleNamespace()
    vpr.cov_items = [
        _make_cov_item("COV-001", "baud tuning"),
        _make_cov_item("COV-002", "reset behavior"),
    ]
    return vpr


# Required STD-003B files (flat basenames, no tb/ prefix)
_REQUIRED_FILES = [
    "test_dut_if.sv",
    "test_dut_pkg.sv",
    "test_dut_seq_item.sv",
    "test_dut_seqr.sv",
    "test_dut_base_seq.sv",
    "test_dut_driver.sv",
    "test_dut_monitor.sv",
    "test_dut_agent.sv",
    "test_dut_env.sv",
    "test_dut_scoreboard.sv",
    "test_dut_coverage_subscriber.sv",
    "test_dut_test.sv",
    "test_dut_smoke_seq.sv",
    "test_dut_regression_test.sv",
    "tb_top.sv",
]


def test_generate_uvm_tb_required_files(tmp_path) -> None:
    """All 15 STD-003B required files are created under tmp_path/tb/."""
    ir = _make_uvm_ir()
    generate_uvm_tb(ir, None, str(tmp_path))
    tb_dir = os.path.join(str(tmp_path), "tb")
    for fname in _REQUIRED_FILES:
        assert os.path.exists(os.path.join(tb_dir, fname)), \
            f"Required file missing: {fname}"
    # build.tcl lives in tb/scripts/vivado/
    assert os.path.exists(
        os.path.join(tb_dir, "scripts", "vivado", "build.tcl")
    )


def test_generate_uvm_tb_pkg_include_order(tmp_path) -> None:
    """pkg.sv include order satisfies STD-003B dependency requirements."""
    ir = _make_uvm_ir()
    generate_uvm_tb(ir, None, str(tmp_path))
    pkg_path = os.path.join(str(tmp_path), "tb", "test_dut_pkg.sv")
    content = open(pkg_path, encoding="utf-8").read()

    # seq_item before seqr
    assert content.index("seq_item") < content.index("seqr"), \
        "seq_item must be included before seqr"
    # seqr before agent
    assert content.index("seqr") < content.index("agent"), \
        "seqr must be included before agent"
    # driver before agent
    assert content.index("driver") < content.index("agent"), \
        "driver must be included before agent"
    # monitor before agent
    assert content.index("monitor") < content.index("agent"), \
        "monitor must be included before agent"
    # agent before env
    assert content.index("_agent") < content.index("_env"), \
        "agent must be included before env"
    # env before test
    assert content.index("_env") < content.index("_test"), \
        "env must be included before test"


def test_generate_uvm_tb_design_name_substitution(tmp_path) -> None:
    """Generated files use the IR design name throughout."""
    ir = _make_uvm_ir("my_block")
    generate_uvm_tb(ir, None, str(tmp_path))
    tb_dir = os.path.join(str(tmp_path), "tb")

    # Interface file exists with design name
    assert os.path.exists(os.path.join(tb_dir, "my_block_if.sv"))

    # pkg.sv contains package name
    pkg_content = open(os.path.join(tb_dir, "my_block_pkg.sv"), encoding="utf-8").read()
    assert "my_block_pkg" in pkg_content

    # tb_top.sv contains DUT instantiation
    top_content = open(os.path.join(tb_dir, "tb_top.sv"), encoding="utf-8").read()
    assert "my_block dut" in top_content or "my_block #(" in top_content


def test_generate_uvm_tb_build_tcl_compile_model(tmp_path) -> None:
    """build.tcl contains required compile invocations for Vivado XSIM."""
    ir = _make_uvm_ir()
    generate_uvm_tb(ir, None, str(tmp_path))
    tcl_path = os.path.join(str(tmp_path), "tb", "scripts", "vivado", "build.tcl")
    content = open(tcl_path, encoding="utf-8").read()

    assert "-L uvm" in content, "build.tcl must pass -L uvm to xvlog"
    assert "work.tb_top" in content, "build.tcl must elaborate work.tb_top"
    assert "_if.sv" in content, "build.tcl must include the interface file"
    assert "_pkg.sv" in content, "build.tcl must include the package file"
    assert "tb_top.sv" in content, "build.tcl must include tb_top.sv"


def test_generate_uvm_tb_with_vplan_stubs(tmp_path) -> None:
    """COV stub files are generated and included in pkg.sv and regression_test.sv."""
    ir = _make_uvm_ir()
    vpr = _make_vplan_result_with_cov()
    generate_uvm_tb(ir, vpr, str(tmp_path))
    tb_dir = os.path.join(str(tmp_path), "tb")

    # Two stub files must exist — naming: seq_RCOV<NNN>_<sanitised_name>.sv
    stub1 = os.path.join(tb_dir, "seq_RCOV001_baud_tuning.sv")
    stub2 = os.path.join(tb_dir, "seq_RCOV002_reset_behavior.sv")
    assert os.path.exists(stub1), f"COV stub missing: {stub1}"
    assert os.path.exists(stub2), f"COV stub missing: {stub2}"

    # pkg.sv must include both stubs
    pkg_content = open(os.path.join(tb_dir, "test_dut_pkg.sv"), encoding="utf-8").read()
    assert "seq_RCOV001_baud_tuning.sv" in pkg_content
    assert "seq_RCOV002_reset_behavior.sv" in pkg_content

    # regression_test.sv must reference both stub class names
    reg_content = open(
        os.path.join(tb_dir, "test_dut_regression_test.sv"), encoding="utf-8"
    ).read()
    assert "seq_RCOV001_baud_tuning" in reg_content
    assert "seq_RCOV002_reset_behavior" in reg_content


def test_generate_uvm_tb_never_overwrites(tmp_path) -> None:
    """Second call to generate_uvm_tb does not overwrite existing files."""
    ir = _make_uvm_ir()

    # First generation
    generate_uvm_tb(ir, None, str(tmp_path))

    # Sentinel content written after first generation
    sentinel = "// SENTINEL — must not be overwritten\n"
    if_path = os.path.join(str(tmp_path), "tb", "test_dut_if.sv")
    with open(if_path, "w", encoding="utf-8") as fh:
        fh.write(sentinel)

    # Second generation — must not overwrite
    generate_uvm_tb(ir, None, str(tmp_path))

    content = open(if_path, encoding="utf-8").read()
    assert content == sentinel, "generate_uvm_tb overwrote an existing file"
