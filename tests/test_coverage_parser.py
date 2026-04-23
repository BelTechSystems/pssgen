# ===========================================================
# FILE:         tests/test_coverage_parser.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for parse_coverage_data() added to agents/results_collector.py
#   (CAE-002). Tests 1–9 use a synthetic xsim log string. Tests 10–14
#   run against the real BALU regression xsim.log.
#
# LAYER:        tests
# PHASE:        v4 (CAE)
#
# HISTORY:
#   0.1.0  2026-04-23  SB  Initial — CAE-002
#
# ===========================================================

import os
import pytest

from agents.results_collector import parse_coverage_data

# ---------------------------------------------------------------------------
# Synthetic log fixture
# ---------------------------------------------------------------------------

SYNTHETIC_LOG = """\
UVM_INFO @ 0: reporter [UVM/RELNOTES] ...
UVM_INFO test.sv(75) @ 315000: uvm_test_top.env_h.agent.seqr@@cov001 [RCOV001] BAUD_TUNING write=0x10d6 readback=0x10d6
UVM_WARNING test.sv(42) @ 500000: uvm_test_top.env_h.agent.seqr@@cov002 [RCOV002] axi_poll timeout - addr=0x00000004 mask=0x00000040 exp=0x00000000 got=0x00000140
UVM_INFO test.sv(65) @ 600000: uvm_test_top.env_h.cov [COV] axi_transaction_cg coverage: 94.8%
UVM_INFO test.sv(146) @ 1525000: reporter [SB] Scoreboard check_phase: 0 error(s)
UVM_INFO test.sv(18601) @ 1525000: reporter [UVM/RELNOTES]

--- UVM Report Summary ---

** Report counts by severity
UVM_INFO :   5
UVM_WARNING :   1
UVM_ERROR :   0
UVM_FATAL :   0

$finish called at time : 1525 ns
"""

SYNTHETIC_LOG_NO_COV = """\
UVM_INFO @ 0: reporter [RNTST] Running test ...
--- UVM Report Summary ---
** Report counts by severity
UVM_INFO :   1
UVM_WARNING :   0
UVM_ERROR :   0
UVM_FATAL :   0
$finish called at time : 100 ns
"""

BALU_LOG = os.path.join(
    os.path.dirname(__file__),
    "..", "output", "balu_ral_session2", "tb", "scripts", "vivado", "xsim.log",
)


@pytest.fixture
def synth_result(tmp_path):
    log = tmp_path / "xsim.log"
    log.write_text(SYNTHETIC_LOG, encoding="utf-8")
    return parse_coverage_data(str(log))


# ---------------------------------------------------------------------------
# Tests 1–9 — synthetic log
# ---------------------------------------------------------------------------

def test_uvm_counts(synth_result):
    c = synth_result["uvm_counts"]
    assert c["info"] == 5
    assert c["warning"] == 1
    assert c["error"] == 0
    assert c["fatal"] == 0


def test_coverage_pct(synth_result):
    assert synth_result["coverage_pct"] == 94.8


def test_simulation_time(synth_result):
    assert synth_result["simulation_time_ns"] == 1525.0


def test_cov001_pass(synth_result):
    assert synth_result["sequences"][0]["seq_id"] == "COV-001"
    assert synth_result["sequences"][0]["status"] == "PASS"


def test_cov002_timeout(synth_result):
    assert synth_result["sequences"][1]["seq_id"] == "COV-002"
    assert synth_result["sequences"][1]["status"] == "TIMEOUT"


def test_cov002_timeout_details(synth_result):
    to = synth_result["sequences"][1]["timeouts"][0]
    assert to["addr"] == "0x00000004"
    assert to["got"] == "0x00000140"


def test_scoreboard_zero_errors(synth_result):
    assert synth_result["scoreboard"]["errors"] == 0


def test_scoreboard_not_disabled(synth_result):
    assert synth_result["scoreboard"]["disabled"] is False


def test_missing_coverage_line(tmp_path):
    log = tmp_path / "xsim_nocov.log"
    log.write_text(SYNTHETIC_LOG_NO_COV, encoding="utf-8")
    result = parse_coverage_data(str(log))
    assert result["coverage_pct"] == -1.0


# ---------------------------------------------------------------------------
# Tests 10–14 — real BALU xsim.log
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def balu_result():
    return parse_coverage_data(BALU_LOG)


def test_balu_log_parses(balu_result):
    required = {
        "sim_log", "parsed_at", "simulation_time_ns", "uvm_counts",
        "coverage_pct", "sequences", "slverr_events", "scoreboard",
        "assertions_fired",
    }
    assert required.issubset(balu_result.keys())


def test_balu_coverage_pct(balu_result):
    assert balu_result["coverage_pct"] == 94.8


def test_balu_sequence_count(balu_result):
    assert len(balu_result["sequences"]) == 19


def test_balu_cov001_pass(balu_result):
    cov001 = next(s for s in balu_result["sequences"] if s["seq_id"] == "COV-001")
    assert cov001["status"] == "PASS"


def test_balu_slverr_count(balu_result):
    assert len(balu_result["slverr_events"]) == 3
