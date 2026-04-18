# ===========================================================
# FILE:         agents/vsl_validator.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Pre-generation lint module for VSL stimulus strings in coverage goal
#   dicts. Validates PHASE_1 goals against authoring rules V-001 through
#   V-007, reports warnings and errors, and raises ValueError in strict
#   mode when errors are present.
#
# LAYER:        3 — agents
# PHASE:        D-034
#
# FUNCTIONS:
#   validate_coverage_goals(goals, known_registers, strict)
#     Validate a list of coverage goal dicts against VSL authoring rules.
#   format_validation_report(results)
#     Render a human-readable validation report string.
#
# DEPENDENCIES:
#   Standard library:  re
#   Internal:          agents.scaffold_gen (parse_vsl_stimulus)
#
# HISTORY:
#   D-034  2026-04-18  SB  Initial implementation
#
# ===========================================================
"""agents/vsl_validator.py — VSL stimulus authoring quality gate.

Phase: D-034
Layer: 3 (agents)

Validates coverage goal VSL strings against a set of authoring rules
(V-001 through V-007). Used both as a CLI flag (--validate-vsl) and
as a non-blocking pre-generation lint step during scaffold generation.
"""
from __future__ import annotations

import re as _re
from typing import Optional

from agents.scaffold_gen import parse_vsl_stimulus


def validate_coverage_goals(
    goals: list[dict],
    known_registers: dict[str, str],
    strict: bool = False,
) -> list[dict]:
    """Validate VSL stimulus strings in coverage goal dicts.

    Applies rules V-001 through V-007 to every goal where
    seq_status == "PHASE_1". Non-PHASE_1 goals receive a pass result
    with no checks applied.

    Args:
        goals:            List of parsed coverage goal dicts from vplan_parser.
        known_registers:  Dict mapping lowercase hex addr string → register name,
                          e.g. {"0x00": "CTRL", "0x04": "STATUS"}.
        strict:           If True, raise ValueError when any error is found.
                          Warnings never cause a raise.

    Returns:
        List of result dicts, one per goal:
          {"id": str, "name": str, "passed": bool,
           "warnings": list[str], "errors": list[str]}

    Raises:
        ValueError: If strict=True and any goal has validation errors.
    """
    # Normalise known_registers keys to lowercase for consistent comparison.
    norm_regs: dict[str, str] = {k.lower(): v for k, v in known_registers.items()}

    results: list[dict] = []

    for goal in goals:
        cov_id        = goal.get("id", "")
        name          = goal.get("name", "")
        seq_status    = (goal.get("seq_status", "NONE") or "NONE").upper()
        seq_review    = (goal.get("seq_review", "DRAFT") or "DRAFT").upper()
        vsl_notes     = goal.get("vsl_notes", "") or ""
        coverage_type = goal.get("coverage_type", "") or ""
        strat         = goal.get("stimulus_strategy", "") or ""
        vsl_steps     = goal.get("vsl_steps") or []

        # Ensure vsl_steps is a parsed list (may be raw string in some paths)
        if isinstance(vsl_steps, str):
            try:
                vsl_steps = parse_vsl_stimulus(vsl_steps)
            except ValueError:
                vsl_steps = []
        elif not isinstance(vsl_steps, list):
            vsl_steps = []

        warnings: list[str] = []
        errors:   list[str] = []

        if seq_status != "PHASE_1":
            results.append({
                "id": cov_id, "name": name,
                "passed": True, "warnings": [], "errors": [],
            })
            continue

        # V-007: PHASE_1 goal has no VSL steps
        if not vsl_steps:
            errors.append("V-007: PHASE_1 goal has no VSL steps")

        # Collect all addresses used in VSL steps
        step_addrs = {
            s["params"].get("addr", "").lower()
            for s in vsl_steps
            if "addr" in s.get("params", {})
        }
        step_actions = {s["action"] for s in vsl_steps}

        # V-001: MUST_USE:INVALID_ADDR
        if "MUST_USE:INVALID_ADDR" in vsl_notes:
            has_invalid = any(a not in norm_regs for a in step_addrs)
            if not has_invalid:
                errors.append(
                    "V-001: MUST_USE:INVALID_ADDR required but no invalid "
                    "address found in VSL steps"
                )

        # V-002: FORBIDDEN:valid_addr_only (alias of V-001)
        if "FORBIDDEN:valid_addr_only" in vsl_notes:
            has_invalid = any(a not in norm_regs for a in step_addrs)
            if not has_invalid:
                errors.append(
                    "V-002: FORBIDDEN:valid_addr_only — no invalid address "
                    "found in VSL steps"
                )

        # V-003: REQUIRES_ACTION:<X>
        for m in _re.finditer(r"REQUIRES_ACTION:(\w+)", vsl_notes):
            action_name = m.group(1)
            warnings.append(
                f"V-003: REQUIRES_ACTION:{action_name} — action not in VSL "
                "grammar, goal deferred to Phase 2"
            )

        # V-004: Structural coverage using STATUS poll
        if coverage_type.lower() == "structural":
            status_addr = "0x04"
            for step in vsl_steps:
                if (
                    step["action"] == "POLL"
                    and step.get("params", {}).get("addr", "").lower() == status_addr
                ):
                    warnings.append(
                        "V-004: Structural goal uses functional loopback path "
                        "— verify intent"
                    )
                    break

        # V-005: "independently" in strategy with <3 steps
        if "independently" in strat.lower() and len(vsl_steps) < 3:
            warnings.append(
                f"V-005: Strategy implies multiple independent stimuli but "
                f"only {len(vsl_steps)} VSL step(s) found"
            )

        # V-006: DRAFT seq_review
        if seq_review == "DRAFT":
            warnings.append(
                "V-006: Seq_Review=DRAFT — goal not approved for generation"
            )

        passed = len(errors) == 0
        results.append({
            "id": cov_id, "name": name,
            "passed": passed, "warnings": warnings, "errors": errors,
        })

    if strict:
        all_errors = [
            f"{r['id']}: {e}"
            for r in results
            for e in r["errors"]
        ]
        if all_errors:
            raise ValueError(
                "VSL validation failed (strict mode):\n"
                + "\n".join(all_errors)
            )

    return results


def format_validation_report(results: list[dict]) -> str:
    """Render a human-readable VSL validation report.

    Args:
        results: List of validation result dicts from validate_coverage_goals.

    Returns:
        Formatted report string with per-goal status and summary line.
    """
    lines: list[str] = ["VSL Validation Report", "=" * 53]

    pass_count  = 0
    warn_count  = 0
    error_count = 0

    for r in results:
        cov_id = r["id"]
        name   = r["name"]
        warns  = r["warnings"]
        errs   = r["errors"]

        if errs:
            tag = "ERROR"
            error_count += 1
        elif warns:
            tag = "WARN "
            warn_count += 1
        else:
            tag = "PASS "
            pass_count += 1

        first_line = f"{tag} {cov_id:<10} {name}"
        all_notes = [f"[{m}]" for m in (errs + warns)]

        if not all_notes:
            lines.append(first_line)
        else:
            lines.append(f"{first_line:<50} {all_notes[0]}")
            indent = " " * 50 + " "
            for note in all_notes[1:]:
                lines.append(f"{indent}{note}")

    lines.append("=" * 53)
    total = len(results)
    lines.append(
        f"{total} goals checked. {pass_count} passed, "
        f"{warn_count} warnings, {error_count} errors."
    )
    return "\n".join(lines)
