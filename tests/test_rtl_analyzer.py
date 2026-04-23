# ===========================================================
# FILE:         tests/test_rtl_analyzer.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/rtl_analyzer.py (CAE-001).
#   Tests 1–8 use a synthetic VHDL string written to a tmp file.
#   Tests 9–12 run the analyzer against the real BALU RTL.
#
# LAYER:        tests
# PHASE:        v4 (CAE)
#
# HISTORY:
#   0.1.0  2026-04-23  SB  Initial — CAE-001
#
# ===========================================================

import json
import os
import pytest

from agents.rtl_analyzer import analyze_vhdl

# ---------------------------------------------------------------------------
# Synthetic VHDL fixture
# ---------------------------------------------------------------------------

TEST_VHDL = """\
entity test_entity is
  port (clk : in std_logic; rst_n : in std_logic;
        data_in : in std_logic_vector(7 downto 0);
        data_out : out std_logic_vector(7 downto 0));
end entity test_entity;

architecture rtl of test_entity is
  signal reg_s : std_logic_vector(7 downto 0);
begin
  REG_p : process(clk)
  begin
    if rising_edge(clk) then
      if rst_n = '0' then
        reg_s <= (others => '0');
      elsif data_in = x"FF" then
        reg_s <= data_in;
      else
        reg_s <= (others => '0');
      end if;
    end if;
  end process REG_p;

  assert data_in /= x"00"
    report "data_in is zero" severity warning;

  data_out <= reg_s;
end architecture rtl;
"""

BALU_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "ip", "buffered_axi_lite_uart", "vhdl", "buffered_axi_lite_uart.vhd"
)


@pytest.fixture
def synth_result(tmp_path):
    vhd = tmp_path / "test_entity.vhd"
    vhd.write_text(TEST_VHDL, encoding="utf-8")
    return analyze_vhdl(str(vhd))


# ---------------------------------------------------------------------------
# Tests 1–8 — synthetic VHDL
# ---------------------------------------------------------------------------

def test_entity_detected(synth_result):
    assert synth_result["entity_name"] == "test_entity"


def test_architecture_detected(synth_result):
    assert synth_result["architecture_name"] == "rtl"


def test_process_detected(synth_result):
    procs = synth_result["processes"]
    assert len(procs) == 1
    assert procs[0]["name"] == "REG_p"


def test_branches_detected(synth_result):
    # Expect: if rising_edge(clk), if rst_n='0', elsif data_in=xFF, else
    assert len(synth_result["branches"]) >= 3


def test_reset_branch_classified(synth_result):
    reset_branches = [
        b for b in synth_result["branches"]
        if b["risk_hint"] == "reset"
    ]
    assert len(reset_branches) >= 1
    conds = [b["condition"] for b in reset_branches]
    assert any("rst_n" in c for c in conds)


def test_assertion_detected(synth_result):
    assert len(synth_result["assertions"]) == 1


def test_assertion_severity(synth_result):
    assert synth_result["assertions"][0]["severity"] == "warning"


def test_summary_counts(synth_result):
    summary = synth_result["summary"]
    assert summary["total_branches"] >= 3
    assert summary["total_processes"] == 1
    assert summary["total_assertions"] == 1


# ---------------------------------------------------------------------------
# Tests 9–12 — real BALU RTL
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def balu_result():
    return analyze_vhdl(BALU_PATH)


def test_balu_file_parses(balu_result):
    required_keys = {
        "file", "analyzed_at", "entity_name", "architecture_name",
        "total_lines", "code_lines", "processes", "branches",
        "fsm_states", "assertions", "registers", "summary",
    }
    assert required_keys.issubset(balu_result.keys())
    assert balu_result["entity_name"] != ""
    assert balu_result["architecture_name"] != ""


def test_balu_has_processes(balu_result):
    assert len(balu_result["processes"]) >= 5


def test_balu_has_branches(balu_result):
    assert len(balu_result["branches"]) >= 20


def test_balu_branch_risk_hints(balu_result):
    """BALU must have reset, boundary, protocol, and normal branches.

    Error branches are absent because BALU's parity/frame-error logic assigns
    ev_*_err_s signals inside branches rather than testing them as conditions.
    Unknown branches indicate parsing failures — must be zero.
    """
    risk_hints = {b["risk_hint"] for b in balu_result["branches"]}
    assert "unknown" not in risk_hints
    assert {"reset", "boundary", "protocol", "normal"}.issubset(risk_hints)
