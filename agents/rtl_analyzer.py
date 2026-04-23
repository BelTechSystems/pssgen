# ===========================================================
# FILE:         agents/rtl_analyzer.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Structural static analyzer for VHDL source files.
#   Extracts processes, branches, FSM states, assertions, and
#   registers without simulation. Forms the foundation of the
#   Coverage Assessment Engine (CAE-001).
#
# LAYER:        3 — agents
# PHASE:        v4 (CAE)
#
# FUNCTIONS:
#   analyze_vhdl(vhdl_path)
#     Parse a VHDL file and return a structural coverage dict.
#
# DEPENDENCIES:
#   Standard library:  re, os, datetime
#   Internal:          none
#
# HISTORY:
#   0.1.0  2026-04-23  SB  Initial implementation — CAE-001
#
# ===========================================================

import re
import os
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_comments(lines: list[str]) -> list[str]:
    """Return lines with inline VHDL -- comments replaced by whitespace.

    Line numbers are preserved (same list length, same indices).
    """
    stripped = []
    for line in lines:
        idx = line.find("--")
        if idx >= 0:
            stripped.append(line[:idx])
        else:
            stripped.append(line)
    return stripped


def _count_code_lines(lines: list[str]) -> int:
    """Count non-blank, non-comment source lines."""
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            count += 1
    return count


def _classify_risk(condition: str) -> str:
    """Return risk_hint string for a branch condition."""
    low = condition.lower()
    if re.search(r"reset|aresetn|\brst", low):
        return "reset"
    if re.search(r"_err|slverr|fault|invalid", low):
        return "error"
    if re.search(r"full|empty|overflow|underflow|\bmax\b|\bmin\b|boundary", low):
        return "boundary"
    if re.search(r"valid|ready|\back\b|\breq\b", low):
        return "protocol"
    return "normal"


def _fmt_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:03d}"


# ---------------------------------------------------------------------------
# Sub-extractors
# ---------------------------------------------------------------------------

def _extract_entity_arch(lines_clean: list[str]) -> tuple[str, str]:
    entity_name = ""
    arch_name = ""
    for line in lines_clean:
        if not entity_name:
            m = re.match(r"\s*entity\s+(\w+)\s+is\b", line, re.IGNORECASE)
            if m:
                entity_name = m.group(1)
        if not arch_name:
            m = re.match(r"\s*architecture\s+(\w+)\s+of\b", line, re.IGNORECASE)
            if m:
                arch_name = m.group(1)
        if entity_name and arch_name:
            break
    return entity_name, arch_name


def _extract_processes(lines_clean: list[str]) -> list[dict[str, Any]]:
    """Return list of process dicts with name, sensitivity_list, line_start, line_end."""
    processes: list[dict[str, Any]] = []
    unnamed_counter = [0]
    n = len(lines_clean)
    i = 0
    while i < n:
        line = lines_clean[i]
        # Labeled: LABEL : process (
        labeled = re.match(
            r"\s*(\w+)\s*:\s*process\s*\(([^)]*)\)", line, re.IGNORECASE
        )
        # Unlabeled: process (...)  or  process(all)
        unlabeled = re.match(
            r"\s*process\s*\(([^)]*)\)", line, re.IGNORECASE
        )
        if labeled:
            name = labeled.group(1)
            sens_raw = labeled.group(2)
            line_start = i + 1  # 1-indexed
        elif unlabeled and not labeled:
            unnamed_counter[0] += 1
            name = f"unnamed_{unnamed_counter[0]}"
            sens_raw = unlabeled.group(1)
            line_start = i + 1
        else:
            i += 1
            continue

        # Parse sensitivity list
        sens_list = [s.strip() for s in re.split(r"[,\s]+", sens_raw) if s.strip()]

        # Find matching end process
        depth = 1
        j = i + 1
        while j < n and depth > 0:
            lj = lines_clean[j].strip().lower()
            if re.search(r"\bprocess\s*\(", lj):
                depth += 1
            if re.search(r"\bend\s+process\b", lj):
                depth -= 1
            j += 1
        line_end = j  # 1-indexed (j already incremented past the end line)

        processes.append({
            "name": name,
            "sensitivity_list": sens_list,
            "line_start": line_start,
            "line_end": line_end,
            "branch_count": 0,  # filled after branch extraction
        })
        i = j
    return processes


def _build_process_map(processes: list[dict]) -> dict[tuple[int, int], str]:
    """Map (line_start, line_end) → process_name for quick lookup."""
    return {(p["line_start"], p["line_end"]): p["name"] for p in processes}


def _process_for_line(processes: list[dict], lineno: int) -> str:
    for p in processes:
        if p["line_start"] <= lineno <= p["line_end"]:
            return p["name"]
    return "toplevel"


def _collect_condition(lines_clean: list[str], start: int, keyword: str) -> str:
    """Collect a potentially multi-line condition starting at lines_clean[start].

    Joins lines until 'then' is found on the same or a later line.
    Returns the condition text between the keyword and 'then'.
    """
    text = lines_clean[start].strip()
    n = len(lines_clean)
    k = start + 1
    while k < n and not re.search(r"\bthen\b", text, re.IGNORECASE):
        text += " " + lines_clean[k].strip()
        k += 1
    # Extract between keyword and 'then'
    m = re.match(
        r"\b" + re.escape(keyword) + r"\s+(.+?)\s+then\b",
        text, re.IGNORECASE | re.DOTALL
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    # Fallback: everything after keyword
    after = re.sub(r"^\b" + re.escape(keyword) + r"\s+", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", after).strip()[:80]


def _extract_branches(
    lines_clean: list[str], processes: list[dict]
) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = []
    branch_counter = 0

    for i, line in enumerate(lines_clean):
        lineno = i + 1
        stripped = line.strip()
        if not stripped:
            continue

        proc_name = _process_for_line(processes, lineno)

        # if <condition> then  (single or multi-line)
        if re.match(r"\bif\b", stripped, re.IGNORECASE) and not re.match(
            r"\bend\s+if\b", stripped, re.IGNORECASE
        ):
            cond = _collect_condition(lines_clean, i, "if")[:80]
            branch_counter += 1
            branches.append({
                "branch_id": _fmt_id("BR", branch_counter),
                "type": "if",
                "condition": cond,
                "process_name": proc_name,
                "line_number": lineno,
                "risk_hint": _classify_risk(cond),
            })
            continue

        # elsif <condition> then  (single or multi-line)
        if re.match(r"\belsif\b", stripped, re.IGNORECASE):
            cond = _collect_condition(lines_clean, i, "elsif")[:80]
            branch_counter += 1
            branches.append({
                "branch_id": _fmt_id("BR", branch_counter),
                "type": "elsif",
                "condition": cond,
                "process_name": proc_name,
                "line_number": lineno,
                "risk_hint": _classify_risk(cond),
            })
            continue

        # else  (standalone keyword — not elsif)
        if re.match(r"\belse\b\s*$", stripped, re.IGNORECASE):
            branch_counter += 1
            branches.append({
                "branch_id": _fmt_id("BR", branch_counter),
                "type": "else",
                "condition": "else",
                "process_name": proc_name,
                "line_number": lineno,
                "risk_hint": "normal",
            })
            continue

        # when others =>
        if re.match(r"\bwhen\s+others\s*=>", stripped, re.IGNORECASE):
            branch_counter += 1
            branches.append({
                "branch_id": _fmt_id("BR", branch_counter),
                "type": "case_others",
                "condition": "others",
                "process_name": proc_name,
                "line_number": lineno,
                "risk_hint": "normal",
            })
            continue

        # when <value> =>  (not others)
        m = re.match(r"\bwhen\s+(.+?)\s*=>", stripped, re.IGNORECASE)
        if m:
            branch_counter += 1
            cond = m.group(1)[:80]
            branches.append({
                "branch_id": _fmt_id("BR", branch_counter),
                "type": "case_when",
                "condition": cond,
                "process_name": proc_name,
                "line_number": lineno,
                "risk_hint": _classify_risk(cond),
            })
            continue

    return branches


def _extract_assertions(lines_clean: list[str], original_lines: list[str]) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    assert_counter = 0
    n = len(lines_clean)
    i = 0
    while i < n:
        line = lines_clean[i].strip()
        m = re.match(r"\bassert\s+(.+)", line, re.IGNORECASE)
        if m:
            assert_counter += 1
            cond_text = m.group(1).strip()
            severity = "error"
            # Look ahead up to 5 lines for severity keyword
            for k in range(i, min(i + 6, n)):
                sev_m = re.search(
                    r"\bseverity\s+(warning|error|failure|note)\b",
                    lines_clean[k], re.IGNORECASE
                )
                if sev_m:
                    severity = sev_m.group(1).lower()
                    break
            assertions.append({
                "assertion_id": _fmt_id("ASSERT", assert_counter),
                "condition": cond_text[:80],
                "severity": severity,
                "line_number": i + 1,
            })
        i += 1
    return assertions


def _extract_fsm_states(lines_clean: list[str]) -> list[dict[str, Any]]:
    """Detect enumeration type definitions as FSM state types."""
    fsm_states: list[dict[str, Any]] = []
    n = len(lines_clean)
    i = 0
    while i < n:
        line = lines_clean[i]
        # type <name>_t is (STATE1, STATE2, ...)
        m = re.match(
            r"\s*type\s+(\w+)\s+is\s*\(([^)]+)\)", line, re.IGNORECASE
        )
        if m:
            type_name = m.group(1)
            states_raw = m.group(2)
            states = [s.strip() for s in states_raw.split(",") if s.strip()]
            if len(states) >= 2:
                # Find a signal of this type
                sig_name = type_name  # fallback
                for j in range(i + 1, min(i + 50, n)):
                    sig_m = re.match(
                        r"\s*signal\s+(\w+)\s*:\s*" + re.escape(type_name) + r"\b",
                        lines_clean[j], re.IGNORECASE,
                    )
                    if sig_m:
                        sig_name = sig_m.group(1)
                        break
                fsm_states.append({
                    "signal_name": sig_name,
                    "states": states,
                    "line_number": i + 1,
                })
        i += 1
    return fsm_states


def _extract_registers(lines_clean: list[str], processes: list[dict]) -> list[dict[str, Any]]:
    """Detect registered signals — assigned inside clocked processes."""
    registers: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Find clocked processes: contain rising_edge(clk) or rising_edge(aclk)
    clocked_procs: list[dict] = []
    for p in processes:
        for i in range(p["line_start"] - 1, min(p["line_end"], len(lines_clean))):
            if re.search(r"rising_edge\s*\(\s*\w*clk\w*\s*\)", lines_clean[i], re.IGNORECASE):
                clocked_procs.append(p)
                break

    for proc in clocked_procs:
        start = proc["line_start"] - 1
        end = min(proc["line_end"], len(lines_clean))
        in_reset = False
        reset_vals: dict[str, str] = {}

        for i in range(start, end):
            line = lines_clean[i].strip()

            # Track reset branch
            if re.search(r"\bif\s+\w*aresetn\w*\s*=\s*['\"]0['\"]", line, re.IGNORECASE) or \
               re.search(r"\bif\s+\w*rst\w*\s*=\s*['\"]1['\"]", line, re.IGNORECASE) or \
               re.search(r"\bif\s+\w*reset\w*\s*=\s*['\"]1['\"]", line, re.IGNORECASE):
                in_reset = True
            elif re.match(r"\belse\b", line, re.IGNORECASE) and in_reset:
                in_reset = False
            elif re.search(r"\bend\s+if\b", line, re.IGNORECASE) and in_reset:
                in_reset = False

            # Signal assignments: sig_name <= value;
            assign_m = re.match(r"(\w+)\s*<=\s*(.+?)\s*;", line)
            if assign_m:
                sig = assign_m.group(1)
                val = assign_m.group(2).strip()
                if in_reset:
                    reset_vals[sig] = val

        # Second pass: collect all assigned signals in clocked process
        in_reset2 = False
        for i in range(start, end):
            line = lines_clean[i].strip()
            if re.search(r"\bif\s+\w*aresetn\w*\s*=\s*['\"]0['\"]", line, re.IGNORECASE) or \
               re.search(r"\bif\s+\w*rst\w*\s*=\s*['\"]1['\"]", line, re.IGNORECASE):
                in_reset2 = True
            elif re.match(r"\belse\b", line, re.IGNORECASE) and in_reset2:
                in_reset2 = False
            elif re.search(r"\bend\s+if\b", line, re.IGNORECASE) and in_reset2:
                in_reset2 = False

            assign_m = re.match(r"(\w+)\s*<=\s*(.+?)\s*;", line)
            if assign_m:
                sig = assign_m.group(1)
                if sig in seen or sig.endswith("_c"):
                    continue
                seen.add(sig)

                has_reset = sig in reset_vals
                reset_val = reset_vals.get(sig, "")

                # Try to determine width from signal declarations
                width = 1
                for dl in lines_clean:
                    wm = re.search(
                        r"\bsignal\s+" + re.escape(sig) +
                        r"\s*:\s*\w+\s*\(\s*(\d+)\s*downto\s*(\d+)\s*\)",
                        dl, re.IGNORECASE,
                    )
                    if wm:
                        width = int(wm.group(1)) - int(wm.group(2)) + 1
                        break

                registers.append({
                    "name": sig,
                    "width": width,
                    "has_reset": has_reset,
                    "reset_value": reset_val,
                    "line_number": i + 1,
                })

    return registers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_vhdl(vhdl_path: str) -> dict[str, Any]:
    """Parse a VHDL file and return structural coverage analysis.

    Args:
        vhdl_path: Path to the VHDL source file.

    Returns:
        Dict conforming to the CAE-001 schema with processes, branches,
        FSM states, assertions, registers, and summary counts.
    """
    with open(vhdl_path, "r", encoding="utf-8", errors="replace") as fh:
        original_lines = fh.readlines()

    lines_clean = _strip_comments(original_lines)
    total_lines = len(original_lines)
    code_lines = _count_code_lines(original_lines)

    entity_name, arch_name = _extract_entity_arch(lines_clean)
    processes = _extract_processes(lines_clean)
    branches = _extract_branches(lines_clean, processes)
    assertions = _extract_assertions(lines_clean, original_lines)
    fsm_states = _extract_fsm_states(lines_clean)
    registers = _extract_registers(lines_clean, processes)

    # Back-fill branch_count into each process
    proc_branch_count: dict[str, int] = {p["name"]: 0 for p in processes}
    for b in branches:
        pname = b["process_name"]
        if pname in proc_branch_count:
            proc_branch_count[pname] += 1
    for p in processes:
        p["branch_count"] = proc_branch_count[p["name"]]

    # Risk hint summary
    risk_counts: dict[str, int] = {
        "reset": 0, "error": 0, "boundary": 0,
        "protocol": 0, "normal": 0, "unknown": 0,
    }
    for b in branches:
        hint = b.get("risk_hint", "unknown")
        risk_counts[hint] = risk_counts.get(hint, 0) + 1

    total_fsm = sum(len(f["states"]) for f in fsm_states)

    summary = {
        "total_branches": len(branches),
        "reset_branches": risk_counts["reset"],
        "error_branches": risk_counts["error"],
        "boundary_branches": risk_counts["boundary"],
        "protocol_branches": risk_counts["protocol"],
        "normal_branches": risk_counts["normal"],
        "unknown_branches": risk_counts["unknown"],
        "total_processes": len(processes),
        "total_assertions": len(assertions),
        "total_fsm_states": total_fsm,
        "estimated_line_coverage_denominator": code_lines,
    }

    return {
        "file": vhdl_path,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "entity_name": entity_name,
        "architecture_name": arch_name,
        "total_lines": total_lines,
        "code_lines": code_lines,
        "processes": processes,
        "branches": branches,
        "fsm_states": fsm_states,
        "assertions": assertions,
        "registers": registers,
        "summary": summary,
    }
