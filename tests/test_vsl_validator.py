# ===========================================================
# FILE:         tests/test_vsl_validator.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/vsl_validator.py — V-001 through V-007 rules,
#   strict mode, format_validation_report, and _gen_cov_stub DRAFT gate.
#
# LAYER:        4 — tests
# PHASE:        D-034
#
# HISTORY:
#   D-034  2026-04-18  SB  Initial implementation
#
# ===========================================================
import logging
import types
import pytest

from agents.vsl_validator import validate_coverage_goals, format_validation_report
from agents.scaffold_gen import _gen_cov_stub, parse_vsl_stimulus


# ── Fixtures / helpers ───────────────────────────────────────────────────────

BALU_REGS = {
    "0x00": "CTRL",    "0x04": "STATUS",  "0x08": "BAUD",
    "0x0c": "TX_DATA", "0x10": "RX_DATA", "0x14": "TX_FIFO",
    "0x18": "RX_FIFO", "0x1c": "IER",     "0x20": "ISR",
    "0x24": "PARITY",  "0x28": "FRAME",   "0x2c": "SCRATCH",
    "0x30": "TIMEOUT", "0x34": "LOOPBACK",
}


def _goal(
    cov_id="COV-001",
    name="test",
    seq_status="PHASE_1",
    vsl="WRITE,addr=0x00,data=0x01",
    vsl_notes="",
    seq_review="APPROVED",
    coverage_type="Functional",
    stimulus_strategy="",
):
    vsl_steps = parse_vsl_stimulus(vsl)
    return {
        "id": cov_id,
        "name": name,
        "seq_status": seq_status,
        "vsl_steps": vsl_steps,
        "vsl_notes": vsl_notes,
        "seq_review": seq_review,
        "coverage_type": coverage_type,
        "stimulus_strategy": stimulus_strategy,
    }


# ── 1. All-valid goals → all pass ────────────────────────────────────────────

def test_all_valid_goals_pass():
    goals = [
        _goal("COV-001", vsl="WRITE,addr=0x00,data=0x01;READ,addr=0x04"),
        _goal("COV-002", vsl="WAIT,cycles=10"),
    ]
    results = validate_coverage_goals(goals, BALU_REGS)
    assert all(r["passed"] for r in results)
    assert all(not r["errors"] and not r["warnings"] for r in results)


# ── 2. V-001: MUST_USE:INVALID_ADDR — no invalid addr → error ───────────────

def test_v001_must_use_invalid_addr_all_valid_raises_error():
    goal = _goal(
        vsl="WRITE,addr=0x00,data=0x01",
        vsl_notes="MUST_USE:INVALID_ADDR",
    )
    results = validate_coverage_goals([goal], BALU_REGS)
    assert not results[0]["passed"]
    assert any("V-001" in e for e in results[0]["errors"])


# ── 3. V-001: MUST_USE:INVALID_ADDR — invalid addr present → pass ───────────

def test_v001_must_use_invalid_addr_with_invalid_passes():
    goal = _goal(
        vsl="WRITE,addr=0x00,data=0x01;READ,addr=0x3C",  # 0x3C not in BALU_REGS
        vsl_notes="MUST_USE:INVALID_ADDR",
    )
    results = validate_coverage_goals([goal], BALU_REGS)
    assert results[0]["passed"]
    assert not any("V-001" in e for e in results[0]["errors"])


# ── 4. V-003: REQUIRES_ACTION → warning only, even in strict mode ───────────

def test_v003_requires_action_is_warning_not_error():
    goal = _goal(vsl_notes="REQUIRES_ACTION:AXI_WRITE_ORDER")
    results = validate_coverage_goals([goal], BALU_REGS)
    assert results[0]["passed"]  # no errors → passed
    assert any("V-003" in w for w in results[0]["warnings"])


def test_v003_requires_action_strict_does_not_raise():
    goal = _goal(vsl_notes="REQUIRES_ACTION:AXI_WRITE_ORDER")
    # strict=True should not raise for warnings-only
    results = validate_coverage_goals([goal], BALU_REGS, strict=True)
    assert results[0]["passed"]


# ── 5. V-004: Structural goal with STATUS poll → warning ────────────────────

def test_v004_structural_status_poll_warns():
    goal = _goal(
        coverage_type="Structural",
        vsl="WRITE,addr=0x00,data=0x03;POLL,addr=0x04,mask=0x02,expect=0x02,timeout=100",
    )
    results = validate_coverage_goals([goal], BALU_REGS)
    assert any("V-004" in w for w in results[0]["warnings"])


# ── 6. V-005: "independently" + <3 steps → warning ──────────────────────────

def test_v005_independently_strategy_few_steps_warns():
    goal = _goal(
        vsl="WRITE,addr=0x00,data=0x01",   # 1 step < 3
        stimulus_strategy="Each bit set and cleared independently via directed stimulus",
    )
    results = validate_coverage_goals([goal], BALU_REGS)
    assert any("V-005" in w for w in results[0]["warnings"])


# ── 7. V-006: DRAFT goal → warning ──────────────────────────────────────────

def test_v006_draft_seq_review_warns():
    goal = _goal(seq_review="DRAFT")
    results = validate_coverage_goals([goal], BALU_REGS)
    assert any("V-006" in w for w in results[0]["warnings"])
    assert results[0]["passed"]  # warning only, still passed


# ── 8. V-007: PHASE_1 with empty vsl_steps → error ──────────────────────────

def test_v007_phase1_empty_vsl_is_error():
    goal = _goal(vsl="")
    results = validate_coverage_goals([goal], BALU_REGS)
    assert not results[0]["passed"]
    assert any("V-007" in e for e in results[0]["errors"])


# ── 9. strict=True with errors → raises ValueError ──────────────────────────

def test_strict_mode_with_errors_raises():
    goal = _goal(vsl="", seq_status="PHASE_1")  # V-007: empty steps
    with pytest.raises(ValueError, match="strict mode"):
        validate_coverage_goals([goal], BALU_REGS, strict=True)


# ── 10. strict=True with only warnings → does not raise ─────────────────────

def test_strict_mode_warnings_only_does_not_raise():
    goal = _goal(seq_review="DRAFT")  # only V-006 warning
    results = validate_coverage_goals([goal], BALU_REGS, strict=True)
    assert results[0]["passed"]


# ── 11. format_validation_report — correct counts in summary ─────────────────

def test_format_validation_report_summary_line():
    goals = [
        _goal("COV-001"),                         # pass
        _goal("COV-002", seq_review="DRAFT"),     # warn
        _goal("COV-003", vsl=""),                 # error
    ]
    results = validate_coverage_goals(goals, BALU_REGS)
    report = format_validation_report(results)
    assert "3 goals checked" in report
    assert "1 passed" in report
    assert "1 warnings" in report
    assert "1 errors" in report
    assert "PASS" in report
    assert "WARN" in report
    assert "ERROR" in report


# ── 12. _gen_cov_stub DRAFT → SEQ_PENDING + warning logged ──────────────────

def test_gen_cov_stub_draft_emits_seq_pending_stub(caplog):
    item = types.SimpleNamespace()
    item.id = "COV-011"
    item.name = "axi_rresp"
    item.seq_status = "PHASE_1"
    item.seq_review = "DRAFT"
    item.stimulus_strategy = ""
    item.boundary_values = ""
    item.linked_requirements = []
    item.vsl_steps = parse_vsl_stimulus(
        "WRITE,addr=0x00,data=0x03;READ,addr=0x3C"
    )
    item.stimulus_vsl = "WRITE,addr=0x00,data=0x03;READ,addr=0x3C"

    with caplog.at_level(logging.WARNING, logger="agents.scaffold_gen"):
        content = _gen_cov_stub("balu", item)

    assert "SEQ_PENDING" in content
    assert "reg_model" not in content
    assert any("DRAFT" in msg for msg in caplog.messages)
