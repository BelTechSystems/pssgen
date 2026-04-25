# ===========================================================
# FILE:         tests/test_effort_controller.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/effort_controller.py. Verifies effort level
#   parameters, convergence guard, unreachable candidate flagging, state
#   persistence, sim failure handling, and CLI --effort validation.
#
# LAYER:        Tests
# PHASE:        D-037
#
# HISTORY:
#   D-037  2026-04-25  SB  Initial implementation; 12 effort controller tests
#
# ===========================================================
"""Unit tests for the effort_controller multi-pass coverage loop."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import toml

from agents.effort_controller import run_effort_loop

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _sim_success() -> dict:
    return {
        "success": True,
        "simulator": "vivado",
        "version": "",
        "coverage_dir": "",
        "xsim_log": "",
        "vivado_log": "",
    }


def _sim_failure() -> dict:
    return {
        "success": False,
        "simulator": "vivado",
        "version": "",
        "coverage_dir": "",
        "xsim_log": "",
        "vivado_log": "",
    }


def _write_pssgen_toml(directory: str, tool: str = "vivado") -> str:
    path = os.path.join(directory, "pssgen.toml")
    config = {"project": {"name": "test_ip"}, "simulator": {"tool": tool}}
    with open(path, "w", encoding="utf-8") as fh:
        toml.dump(config, fh)
    return path


# ---------------------------------------------------------------------------
# Effort parameter tests
# ---------------------------------------------------------------------------


def test_low_effort_params(tmp_path) -> None:
    """level=low produces max_passes=1 and target_pct=95.0."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_failure()):
        result = run_effort_loop(str(tmp_path), toml_path, "low")
    assert result["max_passes"] == 1
    assert result["target_pct"] == 95.0


def test_medium_effort_params(tmp_path) -> None:
    """level=medium produces max_passes=3 and target_pct=98.0."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_failure()):
        result = run_effort_loop(str(tmp_path), toml_path, "medium")
    assert result["max_passes"] == 3
    assert result["target_pct"] == 98.0


def test_high_effort_params(tmp_path) -> None:
    """level=high produces max_passes=5 and target_pct=100.0."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_failure()):
        result = run_effort_loop(str(tmp_path), toml_path, "high")
    assert result["max_passes"] == 5
    assert result["target_pct"] == 100.0


def test_invalid_level_raises(tmp_path) -> None:
    """Unknown effort level raises ValueError with a clear message."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with pytest.raises(ValueError, match="Unknown effort level"):
        run_effort_loop(str(tmp_path), toml_path, "extreme")


# ---------------------------------------------------------------------------
# Convergence behaviour tests
# ---------------------------------------------------------------------------


def test_target_reached_stops_early(tmp_path) -> None:
    """Loop stops after pass 1 when coverage_pct exceeds target on first pass."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_success()):
        with patch("agents.effort_controller._read_coverage_pct", return_value=99.0):
            result = run_effort_loop(str(tmp_path), toml_path, "medium")
    assert result["passes_run"] == 1
    assert result["target_reached"] is True
    assert result["convergence_guard"] is False


def test_max_passes_convergence_guard(tmp_path) -> None:
    """Convergence guard fires when coverage stays below target through all passes."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_success()):
        with patch("agents.effort_controller._read_coverage_pct", return_value=80.0):
            result = run_effort_loop(str(tmp_path), toml_path, "low")
    assert result["passes_run"] == 1
    assert result["convergence_guard"] is True
    assert result["target_reached"] is False


def test_convergence_guard_report_note(tmp_path) -> None:
    """Convergence guard populates report_note with the standard message."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_success()):
        with patch("agents.effort_controller._read_coverage_pct", return_value=80.0):
            result = run_effort_loop(str(tmp_path), toml_path, "low")
    assert result["convergence_guard"] is True
    assert "Maximum passes reached" in result["report_note"]


def test_unreachable_candidates_flagged(tmp_path) -> None:
    """unreachable_candidates is positive when convergence guard fires."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_success()):
        with patch("agents.effort_controller._read_coverage_pct", return_value=80.0):
            result = run_effort_loop(str(tmp_path), toml_path, "low")
    assert result["convergence_guard"] is True
    assert result["unreachable_candidates"] > 0


# ---------------------------------------------------------------------------
# State persistence test
# ---------------------------------------------------------------------------


def test_state_updated_after_loop(tmp_path) -> None:
    """pssgen_state.toml reflects the effort level and final verdict after the loop."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_success()):
        with patch("agents.effort_controller._read_coverage_pct", return_value=99.0):
            result = run_effort_loop(str(tmp_path), toml_path, "low")

    from agents.state_manager import load_state
    state = load_state(str(tmp_path))
    assert state["effort"]["level"] == "low"
    assert state["project"]["last_verdict"] == result["verdict"]


# ---------------------------------------------------------------------------
# Failure handling tests
# ---------------------------------------------------------------------------


def test_simulate_failure_breaks_loop(tmp_path) -> None:
    """Loop exits immediately on sim failure; success=False, passes_run=1."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    with patch("agents.sim_runner.run_simulate", return_value=_sim_failure()):
        result = run_effort_loop(str(tmp_path), toml_path, "medium")
    assert result["success"] is False
    assert result["passes_run"] == 1
    assert result["convergence_guard"] is False


def test_effort_without_simulate_exits(tmp_path, monkeypatch) -> None:
    """--effort without --simulate causes sys.exit(1)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["pssgen", "--effort", "low"])
    from cli import main
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# Verdict completeness test
# ---------------------------------------------------------------------------


def test_verdict_always_issued(tmp_path) -> None:
    """All effort levels produce a non-empty verdict regardless of sim outcome."""
    toml_path = _write_pssgen_toml(str(tmp_path))
    for level in ("low", "medium", "high"):
        with patch("agents.sim_runner.run_simulate", return_value=_sim_failure()):
            result = run_effort_loop(str(tmp_path), toml_path, level)
        assert result["verdict"] != "", f"verdict empty for level={level}"
