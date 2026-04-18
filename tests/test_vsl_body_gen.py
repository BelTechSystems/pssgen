# ===========================================================
# FILE:         tests/test_vsl_body_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for VSL body() generation in _gen_cov_stub() (D-034 Step 4).
#   Covers stub fallback, PHASE_1 generation for each VSL action type,
#   multi-step sequences, and local variable declaration rules.
#
# LAYER:        4 — checkers / tests
# PHASE:        D-034
#
# HISTORY:
#   D-034  2026-04-18  SB  Initial implementation
#
# ===========================================================
import types
import pytest
from agents.scaffold_gen import _gen_cov_stub, parse_vsl_stimulus


def _make_item(
    cov_id="COV-001",
    name="test_goal",
    seq_status="NONE",
    vsl_string="",
    stimulus_strategy="",
    boundary_values="",
    linked_requirements=None,
    seq_review="APPROVED",
):
    """Build a minimal cov_item namespace for testing."""
    item = types.SimpleNamespace()
    item.id = cov_id
    item.name = name
    item.seq_status = seq_status
    item.stimulus_vsl = vsl_string
    item.vsl_steps = parse_vsl_stimulus(vsl_string)
    item.stimulus_strategy = stimulus_strategy
    item.boundary_values = boundary_values
    item.linked_requirements = linked_requirements or []
    item.seq_review = seq_review
    return item


# ── Stub fallback tests ──────────────────────────────────────────────────────

def test_seq_status_none_produces_seq_pending_stub():
    item = _make_item(seq_status="NONE", vsl_string="")
    content = _gen_cov_stub("dut", item)
    assert "SEQ_PENDING" in content
    assert "endtask" in content
    assert "reg_model" not in content


def test_phase1_empty_vsl_produces_seq_pending_stub():
    item = _make_item(seq_status="PHASE_1", vsl_string="")
    content = _gen_cov_stub("dut", item)
    assert "SEQ_PENDING" in content
    assert "reg_model" not in content


# ── PHASE_1 WRITE step ───────────────────────────────────────────────────────

def test_phase1_write_step_produces_reg_model_write():
    item = _make_item(seq_status="PHASE_1", vsl_string="WRITE,addr=0x00,data=0xFF")
    content = _gen_cov_stub("dut", item)
    assert "SEQ_PENDING" not in content
    assert "reg_write(reg_model.CTRL, 0xFF);" in content
    assert "endtask : body" in content


# ── PHASE_1 READ step with expect ────────────────────────────────────────────

def test_phase1_read_with_expect_produces_read_and_uvm_info():
    item = _make_item(
        seq_status="PHASE_1",
        vsl_string="READ,addr=0x04,expect=0x01"
    )
    content = _gen_cov_stub("dut", item)
    assert "SEQ_PENDING" not in content
    assert "reg_read(reg_model.STATUS, rdata);" in content
    assert "expect 0x%0h" in content
    assert "0x01" in content


# ── PHASE_1 WAIT step ────────────────────────────────────────────────────────

def test_phase1_wait_step_produces_repeat_posedge():
    item = _make_item(seq_status="PHASE_1", vsl_string="WAIT,cycles=10")
    content = _gen_cov_stub("dut", item)
    assert "SEQ_PENDING" not in content
    assert "repeat(10) @(posedge vif.clk);" in content


# ── PHASE_1 POLL step ────────────────────────────────────────────────────────

def test_phase1_poll_step_produces_reg_poll_helper():
    item = _make_item(
        seq_status="PHASE_1",
        vsl_string="POLL,addr=0x0C,mask=0x01,expect=0x01,timeout=1000"
    )
    content = _gen_cov_stub("dut", item)
    assert "SEQ_PENDING" not in content
    assert "reg_poll(reg_model.TX_DATA, 0x01, 0x01, 1000);" in content


# ── Multi-step sequence ──────────────────────────────────────────────────────

def test_phase1_multi_step_sequence_produces_all_patterns():
    vsl = "WRITE,addr=0x00,data=0x01;WAIT,cycles=10;READ,addr=0x04,expect=0x01"
    item = _make_item(seq_status="PHASE_1", vsl_string=vsl)
    content = _gen_cov_stub("dut", item)
    assert "Step 1: WRITE" in content
    assert "Step 2: WAIT" in content
    assert "Step 3: READ" in content
    assert "reg_write(reg_model.CTRL" in content
    assert "repeat(10) @(posedge vif.clk);" in content
    assert "reg_read(reg_model.STATUS" in content
    # Verify ordering: WRITE before WAIT before READ
    write_pos = content.index("Step 1: WRITE")
    wait_pos  = content.index("Step 2: WAIT")
    read_pos  = content.index("Step 3: READ")
    assert write_pos < wait_pos < read_pos


# ── Local variable declarations ──────────────────────────────────────────────

def test_local_vars_present_when_read_step_exists():
    item = _make_item(
        seq_status="PHASE_1",
        vsl_string="READ,addr=0x04"
    )
    content = _gen_cov_stub("dut", item)
    assert "uvm_reg_data_t rdata;" in content
    assert "uvm_status_e status;" not in content


def test_local_vars_absent_when_only_poll_step():
    # reg_poll is self-contained; no local vars needed in the body
    item = _make_item(
        seq_status="PHASE_1",
        vsl_string="POLL,addr=0x0C,mask=0x01,expect=0x01,timeout=100"
    )
    content = _gen_cov_stub("dut", item)
    assert "uvm_status_e status;" not in content
    assert "uvm_reg_data_t rdata;" not in content


def test_local_vars_absent_when_only_write_and_wait_steps():
    item = _make_item(
        seq_status="PHASE_1",
        vsl_string="WRITE,addr=0x00,data=0x01;WAIT,cycles=5"
    )
    content = _gen_cov_stub("dut", item)
    assert "uvm_status_e status;" not in content
    assert "uvm_reg_data_t rdata;" not in content
