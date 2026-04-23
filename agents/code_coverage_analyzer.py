# ===========================================================
# FILE:         agents/code_coverage_analyzer.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Cross-references RTL static analysis (rtl_analysis.json) with
#   simulation coverage data (sim_coverage.json) using seven inference
#   rules to classify each RTL branch as covered, a gap, or dead code.
#   Forms the synthesis layer of the Coverage Assessment Engine (CAE-003).
#
# LAYER:        3 — agents
# PHASE:        v4 (CAE)
#
# FUNCTIONS:
#   analyze_code_coverage(rtl_analysis_path, sim_coverage_path, vplan_path)
#     Cross-reference RTL analysis and simulation results; return coverage dict.
#
# DEPENDENCIES:
#   Standard library:  json, re, datetime, pathlib
#   Internal:          none
#
# HISTORY:
#   0.1.0  2026-04-23  SB  Initial implementation — CAE-003
#
# ===========================================================

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Inference rule names (applied in priority order)
# ---------------------------------------------------------------------------

_INFERENCE_RULES: list[str] = [
    "ASSERTION_DEAD_CODE",
    "RESET_ALWAYS_COVERED",
    "PROTOCOL_ALWAYS_COVERED",
    "AXI_PROC_BASELINE",
    "PASS_SEQ_KEYWORD",
    "BOUNDARY_REAL_GAP",
    "NOT_RUN_SEQ_CLASSIFY",
]

# ---------------------------------------------------------------------------
# Register-name → process-name mapping
# Derived from the buffered_axi_lite_uart register map and RTL process names.
# ---------------------------------------------------------------------------

_REG_TO_PROCS: dict[str, set[str]] = {
    "BAUD_TUNING": {"NCO_ACCUM_p", "REG_WRITE_p"},
    "CTRL":        {"REG_WRITE_p", "TX_ENGINE_p", "RX_ENGINE_p"},
    "STATUS":      {"AXI_READ_p",  "STATUS_p"},
    "FIFO_STATUS": {"AXI_READ_p",  "TX_FIFO_p",   "RX_FIFO_p"},
    "TIMEOUT_VAL": {"REG_WRITE_p", "TIMEOUT_p"},
    "INT_STATUS":  {"INT_CTRL_p",  "AXI_READ_p"},
    "INT_ENABLE":  {"REG_WRITE_p", "INT_CTRL_p"},
    "SCRATCH":     {"REG_WRITE_p"},
    "TX_DATA":     {"TX_FIFO_p",   "AXI_WRITE_RESP_p"},
    "RX_DATA":     {"RX_FIFO_p",   "RX_ENGINE_p",    "AXI_READ_p"},
    "TX_LEVEL":    {"TX_FIFO_p",   "TX_ENGINE_p"},
    "RX_LEVEL":    {"RX_FIFO_p",   "RX_ENGINE_p"},
}

# Processes exercised by every AXI read or write transaction.
_AXI_PROCS: frozenset[str] = frozenset({
    "AXI_AW_LATCH_p",
    "AXI_W_LATCH_p",
    "AXI_WRITE_RESP_p",
    "AXI_READ_p",
})

# Processes whose only targeted coverage sequences are NOT_RUN.
# Used to attribute NOT_RUN_SEQ gaps when a process is not covered by PASS sequences.
_NOT_RUN_PROC_TARGETS: dict[str, frozenset[str]] = {
    "COV-012": frozenset({"AXI_AW_LATCH_p", "AXI_W_LATCH_p"}),
    "COV-013": frozenset({"REG_WRITE_p"}),
    "COV-016": frozenset({"TX_ENGINE_p", "RX_ENGINE_p", "REG_WRITE_p"}),
    "COV-018": frozenset({"AXI_WRITE_RESP_p"}),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _covered_procs_from_pass(sequences: list[dict]) -> frozenset[str]:
    """Return processes implied covered by PASS sequence messages.

    Scans each PASS sequence's message list for register-name keywords and maps
    them to RTL process names using _REG_TO_PROCS.
    """
    covered: set[str] = set()
    for seq in sequences:
        if seq.get("status") != "PASS":
            continue
        for msg in seq.get("messages", []):
            upper = msg.upper()
            for reg, procs in _REG_TO_PROCS.items():
                if reg in upper:
                    covered |= procs
    return frozenset(covered)


def _exclusive_not_run_procs(
    sequences: list[dict], covered_procs: frozenset[str]
) -> frozenset[str]:
    """Return processes targeted *only* by NOT_RUN sequences.

    A process is exclusive to NOT_RUN if it appears in _NOT_RUN_PROC_TARGETS for
    at least one NOT_RUN sequence and is NOT present in covered_procs (which
    includes both AXI baseline and PASS-keyword-matched processes).
    """
    not_run_targets: set[str] = set()
    for seq in sequences:
        if seq.get("status") == "NOT_RUN":
            seq_id = seq.get("seq_id", "")
            not_run_targets |= _NOT_RUN_PROC_TARGETS.get(seq_id, frozenset())
    return frozenset(not_run_targets - covered_procs)


def _make_branch_entry(
    br: dict,
    covered: bool,
    confidence: str,
    gap_classification: str | None,
    inference_rule: str,
) -> dict[str, Any]:
    """Assemble a classified branch dict from source branch fields."""
    return {
        "branch_id":        br["branch_id"],
        "type":             br.get("type", "if"),
        "condition":        br.get("condition", ""),
        "process_name":     br.get("process_name", ""),
        "line_number":      br.get("line_number", 0),
        "risk_hint":        br.get("risk_hint", "normal"),
        "covered":          covered,
        "confidence":       confidence,
        "gap_classification": gap_classification,
        "inference_rule":   inference_rule,
    }


def _classify_rtl_branch(
    br: dict,
    covered_procs: frozenset[str],
    exclusive_not_run: frozenset[str],
) -> dict[str, Any]:
    """Apply the seven inference rules to a single RTL branch."""
    risk = br.get("risk_hint", "normal")
    proc = br.get("process_name", "")

    # Rule 2 — reset: synchronous reset arm fires every simulation run.
    if risk == "reset":
        return _make_branch_entry(br, True, "HIGH", None, "RESET_ALWAYS_COVERED")

    # Rule 3 — protocol: AXI handshake conditions fire in any register access.
    if risk == "protocol":
        return _make_branch_entry(br, True, "MEDIUM", None, "PROTOCOL_ALWAYS_COVERED")

    # Rules 4/5 — process covered by AXI baseline or PASS keyword match.
    if proc in covered_procs:
        rule = "AXI_PROC_BASELINE" if proc in _AXI_PROCS else "PASS_SEQ_KEYWORD"
        if risk == "boundary":
            # Rule 6 — boundary in covered process: needs a dedicated test stimulus.
            return _make_branch_entry(br, False, "MEDIUM", "REAL_GAP", "BOUNDARY_REAL_GAP")
        return _make_branch_entry(br, True, "MEDIUM", None, rule)

    # Rule 7 — NOT_RUN_SEQ: process reached only by sequences that never ran.
    if proc in exclusive_not_run:
        return _make_branch_entry(br, False, "LOW", "NOT_RUN_SEQ", "NOT_RUN_SEQ_CLASSIFY")

    # Boundary branches in uncovered processes are still REAL_GAPs.
    if risk == "boundary":
        return _make_branch_entry(br, False, "LOW", "REAL_GAP", "BOUNDARY_REAL_GAP")

    return _make_branch_entry(br, False, "LOW", "UNKNOWN", "UNCLASSIFIED")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_code_coverage(
    rtl_analysis_path: str,
    sim_coverage_path: str,
    vplan_path: str | None = None,
) -> dict[str, Any]:
    """Cross-reference RTL analysis and simulation coverage to classify branches.

    Args:
        rtl_analysis_path: Path to rtl_analysis.json produced by analyze_vhdl().
        sim_coverage_path: Path to sim_coverage.json produced by parse_coverage_data().
        vplan_path:        Optional path to a verification plan JSON (reserved, unused).

    Returns:
        Dict with keys: rtl_analysis, sim_coverage, vplan, analyzed_at,
        total_rtl_branches, total_assertions, total_branches,
        exercised_count, dead_code_count, real_gap_count, not_run_seq_count,
        unknown_count, branch_coverage_pct, adjusted_coverage_pct,
        inference_rules_applied, branches, gap_summary.
    """
    rtl: dict = json.loads(Path(rtl_analysis_path).read_text(encoding="utf-8"))
    sim: dict = json.loads(Path(sim_coverage_path).read_text(encoding="utf-8"))

    sequences: list[dict] = sim.get("sequences", [])
    rtl_branches: list[dict] = rtl.get("branches", [])
    assertions: list[dict] = rtl.get("assertions", [])

    covered_procs = _AXI_PROCS | _covered_procs_from_pass(sequences)
    exclusive_not_run = _exclusive_not_run_procs(sequences, covered_procs)

    output_branches: list[dict] = []
    exercised_count = 0
    dead_code_count = 0
    real_gap_count = 0
    not_run_seq_count = 0
    unknown_count = 0

    # --- classify RTL branches ---
    for br in rtl_branches:
        entry = _classify_rtl_branch(br, covered_procs, exclusive_not_run)
        output_branches.append(entry)
        if entry["covered"]:
            exercised_count += 1
        elif entry["gap_classification"] == "REAL_GAP":
            real_gap_count += 1
        elif entry["gap_classification"] == "NOT_RUN_SEQ":
            not_run_seq_count += 1
        elif entry["gap_classification"] == "UNKNOWN":
            unknown_count += 1

    # --- assertions are always elaboration-time DEAD_CODE (Rule 1) ---
    for asrt in assertions:
        entry = {
            "branch_id":        asrt["assertion_id"],
            "type":             "assertion",
            "condition":        asrt.get("condition", ""),
            "process_name":     None,
            "line_number":      asrt.get("line_number", 0),
            "risk_hint":        "DEAD_CODE",
            "covered":          False,
            "confidence":       "HIGH",
            "gap_classification": "DEAD_CODE",
            "inference_rule":   "ASSERTION_DEAD_CODE",
        }
        output_branches.append(entry)
        dead_code_count += 1

    total_rtl = len(rtl_branches)
    total_assertions = len(assertions)

    # RTL dead code = branches in RTL (not assertions) classified as DEAD_CODE.
    rtl_dead_code = sum(
        1 for b in output_branches[:total_rtl]
        if b["gap_classification"] == "DEAD_CODE"
    )

    if total_rtl > 0:
        branch_coverage_pct = round(exercised_count / total_rtl * 100, 2)
    else:
        branch_coverage_pct = 0.0

    denom = total_rtl - rtl_dead_code
    adjusted_coverage_pct = round(exercised_count / denom * 100, 2) if denom > 0 else 0.0

    # --- gap summary ---
    gap_summary: dict[str, list[str]] = {
        "dead_code":    [],
        "defensive":    [],
        "not_run_seq":  [],
        "real_gap":     [],
        "unknown":      [],
    }
    for b in output_branches:
        gc = b.get("gap_classification")
        if gc == "DEAD_CODE":
            gap_summary["dead_code"].append(b["branch_id"])
        elif gc == "DEFENSIVE":
            gap_summary["defensive"].append(b["branch_id"])
        elif gc == "NOT_RUN_SEQ":
            gap_summary["not_run_seq"].append(b["branch_id"])
        elif gc == "REAL_GAP":
            gap_summary["real_gap"].append(b["branch_id"])
        elif gc == "UNKNOWN":
            gap_summary["unknown"].append(b["branch_id"])

    return {
        "rtl_analysis":            str(rtl_analysis_path),
        "sim_coverage":            str(sim_coverage_path),
        "vplan":                   str(vplan_path) if vplan_path else None,
        "analyzed_at":             datetime.now(timezone.utc).isoformat(),
        "total_rtl_branches":      total_rtl,
        "total_assertions":        total_assertions,
        "total_branches":          total_rtl + total_assertions,
        "exercised_count":         exercised_count,
        "dead_code_count":         dead_code_count,
        "real_gap_count":          real_gap_count,
        "not_run_seq_count":       not_run_seq_count,
        "unknown_count":           unknown_count,
        "branch_coverage_pct":     branch_coverage_pct,
        "adjusted_coverage_pct":   adjusted_coverage_pct,
        "inference_rules_applied": _INFERENCE_RULES,
        "branches":                output_branches,
        "gap_summary":             gap_summary,
    }
