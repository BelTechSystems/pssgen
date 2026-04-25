# ===========================================================
# FILE:         agents/state_manager.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Manages pssgen_state.toml, the machine-written runtime state file that
#   persists simulator selection, effort level, and project metadata across
#   CLI invocations. Never edited by the engineer. Distinct from pssgen.toml
#   which holds user configuration. Created on first access with default
#   schema; updated by pssgen CLI after each invocation.
#
# LAYER:        3 — agents
# PHASE:        D-036
#
# FUNCTIONS:
#   load_state(project_root)
#     Read pssgen_state.toml; create with defaults if absent.
#   save_state(project_root, state)
#     Write state dict to pssgen_state.toml.
#   get_simulator(project_root)
#     Return current simulator tool name.
#   set_simulator(project_root, tool)
#     Validate and persist simulator selection.
#   get_effort(project_root)
#     Return current effort block dict.
#   set_effort(project_root, level)
#     Derive and persist max_passes/target_pct from level name.
#   update_project(project_root, **kwargs)
#     Merge keyword arguments into [project] block and save.
#
# DEPENDENCIES:
#   Standard library:  os, copy
#   Internal:          (none)
#   Third-party:       toml
#
# HISTORY:
#   D-036  2026-04-25  SB  Initial implementation
#
# ===========================================================
"""agents/state_manager.py — pssgen_state.toml runtime state manager."""

from __future__ import annotations

import copy
import os
from typing import Any

import toml

_STATE_FILENAME = "pssgen_state.toml"

_VALID_TOOLS = {"vivado", "verilator", "icarus", "questa"}

_EFFORT_RULES: dict[str, dict[str, Any]] = {
    "low":    {"max_passes": 1, "target_pct": 95.0},
    "medium": {"max_passes": 3, "target_pct": 98.0},
    "high":   {"max_passes": 5, "target_pct": 100.0},
}

_DEFAULT_STATE: dict[str, Any] = {
    "simulator": {
        "tool": "vivado",
        "version": "",
        "xcrg_path": "",
        "coverage_dir": "",
    },
    "effort": {
        "level": "low",
        "max_passes": 1,
        "target_pct": 95.0,
    },
    "project": {
        "ip_name": "",
        "last_run": "",
        "last_verdict": "",
    },
}


def _state_path(project_root: str) -> str:
    return os.path.join(project_root, _STATE_FILENAME)


def load_state(project_root: str) -> dict[str, Any]:
    """Read pssgen_state.toml; create with defaults if the file is absent."""
    path = _state_path(project_root)
    if not os.path.exists(path):
        state = copy.deepcopy(_DEFAULT_STATE)
        save_state(project_root, state)
        return state
    with open(path, "r", encoding="utf-8") as fh:
        return toml.load(fh)


def save_state(project_root: str, state: dict[str, Any]) -> None:
    """Write state dict to pssgen_state.toml."""
    path = _state_path(project_root)
    with open(path, "w", encoding="utf-8") as fh:
        toml.dump(state, fh)


def get_simulator(project_root: str) -> str:
    """Return the currently configured simulator tool name."""
    state = load_state(project_root)
    return state["simulator"]["tool"]


def set_simulator(project_root: str, tool: str) -> None:
    """Validate and persist simulator tool name.

    Raises:
        ValueError: If tool is not one of the supported simulator names.
    """
    if tool not in _VALID_TOOLS:
        raise ValueError(
            f"Unknown simulator {tool!r}. "
            f"Supported values: {', '.join(sorted(_VALID_TOOLS))}"
        )
    state = load_state(project_root)
    state["simulator"]["tool"] = tool
    save_state(project_root, state)


def get_effort(project_root: str) -> dict[str, Any]:
    """Return the current effort block as a dict."""
    state = load_state(project_root)
    return state["effort"]


def set_effort(project_root: str, level: str) -> None:
    """Derive and persist max_passes/target_pct from effort level name.

    Raises:
        ValueError: If level is not low, medium, or high.
    """
    if level not in _EFFORT_RULES:
        raise ValueError(
            f"Unknown effort level {level!r}. "
            f"Supported values: {', '.join(sorted(_EFFORT_RULES))}"
        )
    state = load_state(project_root)
    state["effort"]["level"] = level
    state["effort"].update(_EFFORT_RULES[level])
    save_state(project_root, state)


def update_project(project_root: str, **kwargs: Any) -> None:
    """Merge keyword arguments into the [project] block and save."""
    state = load_state(project_root)
    state["project"].update(kwargs)
    save_state(project_root, state)
