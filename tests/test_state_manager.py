# ===========================================================
# FILE:         tests/test_state_manager.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/state_manager.py. Verifies default creation,
#   round-trip save/load, effort level derivation, simulator validation,
#   project field updates, and .gitignore presence.
#
# LAYER:        Tests
# PHASE:        D-036
#
# HISTORY:
#   D-036  2026-04-25  SB  Initial implementation; 10 state manager tests
#
# ===========================================================
"""Unit tests for the pssgen_state.toml state manager."""

from __future__ import annotations

import os

import pytest

from agents.state_manager import (
    get_effort,
    get_simulator,
    load_state,
    save_state,
    set_effort,
    set_simulator,
    update_project,
)

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_GITIGNORE = os.path.join(_REPO_ROOT, ".gitignore")


def test_load_creates_default(tmp_path) -> None:
    """load_state on a directory with no state file creates default schema."""
    state = load_state(str(tmp_path))

    assert state["simulator"]["tool"] == "vivado"
    assert state["effort"]["level"] == "low"
    assert state["effort"]["max_passes"] == 1
    assert state["effort"]["target_pct"] == 95.0
    assert state["project"]["ip_name"] == ""
    assert os.path.exists(tmp_path / "pssgen_state.toml")


def test_save_and_reload(tmp_path) -> None:
    """save_state then load_state returns the same data."""
    state = load_state(str(tmp_path))
    state["project"]["ip_name"] = "my_uart"
    save_state(str(tmp_path), state)

    reloaded = load_state(str(tmp_path))
    assert reloaded["project"]["ip_name"] == "my_uart"


def test_set_effort_low(tmp_path) -> None:
    """level=low derives max_passes=1, target_pct=95.0."""
    set_effort(str(tmp_path), "low")
    effort = get_effort(str(tmp_path))

    assert effort["level"] == "low"
    assert effort["max_passes"] == 1
    assert effort["target_pct"] == 95.0


def test_set_effort_medium(tmp_path) -> None:
    """level=medium derives max_passes=3, target_pct=98.0."""
    set_effort(str(tmp_path), "medium")
    effort = get_effort(str(tmp_path))

    assert effort["level"] == "medium"
    assert effort["max_passes"] == 3
    assert effort["target_pct"] == 98.0


def test_set_effort_high(tmp_path) -> None:
    """level=high derives max_passes=5, target_pct=100.0."""
    set_effort(str(tmp_path), "high")
    effort = get_effort(str(tmp_path))

    assert effort["level"] == "high"
    assert effort["max_passes"] == 5
    assert effort["target_pct"] == 100.0


def test_invalid_effort_raises(tmp_path) -> None:
    """Unknown effort level raises ValueError with a clear message."""
    with pytest.raises(ValueError, match="Unknown effort level"):
        set_effort(str(tmp_path), "extreme")


def test_set_simulator_valid(tmp_path) -> None:
    """All four supported simulator names are accepted without error."""
    for tool in ("vivado", "verilator", "icarus", "questa"):
        set_simulator(str(tmp_path), tool)
        assert get_simulator(str(tmp_path)) == tool


def test_set_simulator_invalid(tmp_path) -> None:
    """Unsupported simulator names raise ValueError."""
    for tool in ("vcs", "incisive"):
        with pytest.raises(ValueError, match="Unknown simulator"):
            set_simulator(str(tmp_path), tool)


def test_update_project_fields(tmp_path) -> None:
    """update_project merges ip_name, last_run, last_verdict correctly."""
    update_project(str(tmp_path), ip_name="balu", last_run="2026-04-25", last_verdict="PASS")
    state = load_state(str(tmp_path))

    assert state["project"]["ip_name"] == "balu"
    assert state["project"]["last_run"] == "2026-04-25"
    assert state["project"]["last_verdict"] == "PASS"


def test_gitignore_contains_state_toml() -> None:
    """pssgen_state.toml is listed in .gitignore."""
    assert os.path.exists(_GITIGNORE), ".gitignore not found"
    with open(_GITIGNORE, encoding="utf-8") as fh:
        content = fh.read()
    assert "pssgen_state.toml" in content
