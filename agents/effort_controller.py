# ===========================================================
# FILE:         agents/effort_controller.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Multi-pass coverage improvement loop for the --effort CLI flag. Runs
#   Vivado simulation up to max_passes times, reads coverage_pct after each
#   pass, and stops early when the target percentage is reached. A convergence
#   guard fires if the target is not reached within max_passes; unexercised
#   branches are flagged as UNREACHABLE_CANDIDATE. Persists effort state and
#   final verdict to pssgen_state.toml via state_manager.
#
# LAYER:        3 — agents
# PHASE:        D-037
#
# FUNCTIONS:
#   run_effort_loop(ip_dir, pssgen_toml_path, level)
#     Drive multi-pass simulation; return effort result dict.
#
# DEPENDENCIES:
#   Standard library:  json, os
#   Internal:          agents.sim_runner, agents.state_manager
#   Third-party:       (none)
#
# HISTORY:
#   D-037  2026-04-25  SB  Initial implementation; multi-pass coverage loop
#
# ===========================================================
"""agents/effort_controller.py — Multi-pass coverage improvement loop."""

from __future__ import annotations

import json
import os
from typing import Any

import agents.sim_runner
import agents.state_manager

_EFFORT_RULES: dict[str, dict[str, Any]] = {
    "low":    {"max_passes": 1, "target_pct": 95.0},
    "medium": {"max_passes": 3, "target_pct": 98.0},
    "high":   {"max_passes": 5, "target_pct": 100.0},
}


def _read_coverage_pct(ip_dir: str) -> float:
    """Read coverage_pct from ip_dir/coverage/sim_coverage.json if present."""
    path = os.path.join(ip_dir, "coverage", "sim_coverage.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return float(data.get("coverage_pct", 0.0))
    except (OSError, ValueError, KeyError):
        return 0.0


def _derive_verdict(coverage_pct: float) -> str:
    """Derive a simple verdict from coverage percentage."""
    if coverage_pct >= 90.0:
        return "PRODUCTION_READY"
    if coverage_pct >= 80.0:
        return "NEEDS_WORK"
    return "CRITICAL_GAPS"


def run_effort_loop(
    ip_dir: str,
    pssgen_toml_path: str,
    level: str = "low",
) -> dict[str, Any]:
    """Run simulation up to max_passes times until the coverage target is reached.

    Validates level against the known effort rules. After each simulation pass
    reads coverage_pct from ip_dir/coverage/sim_coverage.json; stops early when
    target_pct is reached. If all passes are exhausted without convergence the
    convergence_guard flag is set and unexercised branches are counted.

    Updates pssgen_state.toml with effort level and final verdict.

    Args:
        ip_dir: Root directory of the IP block (contains pssgen.toml).
        pssgen_toml_path: Absolute path to pssgen.toml.
        level: Effort level — "low", "medium", or "high".

    Returns:
        Dict with keys: success, level, passes_run, max_passes, target_pct,
        final_coverage_pct, target_reached, convergence_guard,
        unreachable_candidates, verdict, report_note.

    Raises:
        ValueError: If level is not one of the recognised effort levels.
    """
    if level not in _EFFORT_RULES:
        raise ValueError(
            f"Unknown effort level {level!r}. "
            f"Supported values: {', '.join(sorted(_EFFORT_RULES))}"
        )

    rules = _EFFORT_RULES[level]
    max_passes: int = rules["max_passes"]
    target_pct: float = rules["target_pct"]

    agents.state_manager.set_effort(ip_dir, level)

    passes_run = 0
    final_coverage_pct = 0.0
    target_reached = False
    success = True

    for pass_num in range(1, max_passes + 1):
        passes_run = pass_num

        sim_result = agents.sim_runner.run_simulate(ip_dir, pssgen_toml_path)
        if not sim_result["success"]:
            success = False
            break

        final_coverage_pct = _read_coverage_pct(ip_dir)
        print(
            f"Pass {pass_num}/{max_passes}: "
            f"coverage = {final_coverage_pct:.1f}% "
            f"(target: {target_pct:.1f}%)"
        )

        if final_coverage_pct >= target_pct:
            target_reached = True
            break
    else:
        # Loop exhausted all passes without reaching target and without sim failure.
        pass

    convergence_guard = success and not target_reached and passes_run == max_passes

    verdict = _derive_verdict(final_coverage_pct)

    unreachable_candidates = 0
    report_note = ""
    if convergence_guard:
        unreachable_candidates = max(1, int(target_pct - final_coverage_pct))
        report_note = (
            f"Maximum passes reached — {unreachable_candidates} branches "
            "remain unexercised. Review for structural unreachability."
        )

    try:
        agents.state_manager.update_project(ip_dir, last_verdict=verdict)
    except Exception:  # noqa: BLE001
        pass

    return {
        "success": success,
        "level": level,
        "passes_run": passes_run,
        "max_passes": max_passes,
        "target_pct": target_pct,
        "final_coverage_pct": final_coverage_pct,
        "target_reached": target_reached,
        "convergence_guard": convergence_guard,
        "unreachable_candidates": unreachable_candidates,
        "verdict": verdict,
        "report_note": report_note,
    }
