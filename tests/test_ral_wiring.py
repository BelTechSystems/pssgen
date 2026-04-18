# ===========================================================
# FILE:         tests/test_ral_wiring.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for RAL wiring Session 1 changes in scaffold_gen.py.
#   Covers _addr_to_reg() lookup table, reg_write/reg_read/reg_poll
#   helper generation, and placeholder elimination in BALU bodies.
#
# LAYER:        4 — checkers / tests
# PHASE:        D-034 / RAL Session 1
#
# HISTORY:
#   RAL-S1  2026-04-18  SB  Initial implementation
#
# ===========================================================
import logging
import types
import pytest

from agents.scaffold_gen import _addr_to_reg, _gen_cov_stub, parse_vsl_stimulus


def _make_item(
    vsl_string,
    cov_id="COV-001",
    name="test_goal",
):
    """Build a minimal cov_item for testing."""
    item = types.SimpleNamespace()
    item.id = cov_id
    item.name = name
    item.seq_status = "PHASE_1"
    item.seq_review = "APPROVED"
    item.stimulus_strategy = ""
    item.boundary_values = ""
    item.linked_requirements = []
    item.stimulus_vsl = vsl_string
    item.vsl_steps = parse_vsl_stimulus(vsl_string)
    return item


# ── addr_to_reg lookup table ─────────────────────────────────────────────────

def test_addr_to_reg_ctrl():
    assert _addr_to_reg("0x00") == "CTRL"


def test_addr_to_reg_baud():
    assert _addr_to_reg("0x08") == "BAUD"


def test_addr_to_reg_isr():
    assert _addr_to_reg("0x20") == "ISR"


def test_addr_to_reg_unknown_returns_placeholder_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="agents.scaffold_gen"):
        result = _addr_to_reg("0x3C")
    assert result == "reg_003c"
    assert any("reg_003c" in msg for msg in caplog.messages)


# ── reg_write / reg_read / reg_poll generation ───────────────────────────────

def test_cov001_body_uses_reg_write_baud():
    item = _make_item(
        "WRITE,addr=0x08,data=0x000010D6",
        cov_id="COV-001",
        name="BAUD_TUNING",
    )
    content = _gen_cov_stub("dut", item)
    assert "reg_write(reg_model.BAUD" in content


def test_cov007_body_uses_reg_poll_isr():
    item = _make_item(
        "POLL,addr=0x20,mask=0x01,expect=0x01,timeout=100",
        cov_id="COV-007",
        name="INT_STATUS_each_bit",
    )
    content = _gen_cov_stub("dut", item)
    assert "reg_poll(reg_model.ISR" in content


def test_cov015_body_uses_reg_write_ctrl():
    item = _make_item(
        "WRITE,addr=0x00,data=0x80",
        cov_id="COV-015",
        name="RESET_VALUES",
    )
    content = _gen_cov_stub("dut", item)
    assert "reg_write(reg_model.CTRL" in content


def test_no_placeholder_reg_names_in_balu_bodies():
    """Verify no generated body() contains old-style reg_XXXX placeholders."""
    balu_addrs = [
        "0x00", "0x04", "0x08", "0x0C",
        "0x10", "0x14", "0x18", "0x1C",
        "0x20", "0x24", "0x28", "0x2C",
        "0x30", "0x34",
    ]
    for addr in balu_addrs:
        item = _make_item(f"WRITE,addr={addr},data=0x01")
        content = _gen_cov_stub("dut", item)
        assert "reg_model.reg_00" not in content, (
            f"Placeholder reg_00XX found for known address {addr}"
        )
