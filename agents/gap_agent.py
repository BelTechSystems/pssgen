# ===========================================================
# FILE:         agents/gap_agent.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Bidirectional gap analysis between PSS coverage labels and formal
#   requirements. Direction A (ERROR): requirements not covered by any
#   PSS label. Direction B (WARNING): PSS labels from intent or inferred
#   sources with no traceable requirement ID. Waivers suppress errors
#   for explicitly waived items. Writes a structured gap report file.
#
# LAYER:        3 — agents
# PHASE:        v3b
#
# FUNCTIONS:
#   analyse_gaps(ir, intent_result, req_result, coverage_labels)
#     Build a GapReport from bidirectional gap analysis.
#   update_gaps_from_coverage(report, coverage)
#     Update GapReport with simulation coverage data; mark hit/miss/unknown.
#   write_gap_report(report, out_path)
#     Write the formatted gap report to a file; return the path.
#   format_console_summary(report)
#     Return a single-line console summary of gap counts.
#
# DEPENDENCIES:
#   Standard library:  dataclasses, typing, os, datetime
#   Internal:          ir, agents.coverage_reader
#
# HISTORY:
#   v3b      2026-03-28  SB  Initial implementation; bidirectional gap analysis
#   v3c-b    2026-03-29  SB  Added coverage hit/miss tracking and update_gaps_from_coverage
#   v5a-prep 2026-04-06  SB  inline_requirements Direction A; req mode in report header (D-025)
#
# ===========================================================
"""agents/gap_agent.py — Bidirectional requirements traceability gap analysis.

Phase: v3b
Layer: 3 (agents)

Analyses gaps between PSS coverage labels and formal requirements files.
Reports uncovered requirements as errors, untraced intent labels as warnings,
and records explicitly waived items.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import os

from ir import IR
from agents.coverage_reader import CoverageResult


@dataclass
class GapReport:
    """Result of a bidirectional gap analysis run.

    Attributes:
        design_name: Name of the design under analysis.
        errors: Direction-A entries: requirements with no PSS coverage label.
        warnings: Direction-B entries: PSS labels with no traceable req ID.
        waivers: Explicitly waived items (from req_result or coverage_labels).
        coverage_labels: Full coverage label list used in the analysis.
        req_result: ReqParseResult used, or None if no .req file.
        intent_result: IntentParseResult used, or None if no .intent file.
        input_file: HDL input file path.
        intent_path: Intent file path used, or empty string.
        req_path: Requirements file path used, or empty string.
    """
    design_name: str
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    waivers: list[dict] = field(default_factory=list)
    coverage_labels: list[dict] = field(default_factory=list)
    req_result: Optional[object] = None
    intent_result: Optional[object] = None
    input_file: str = ""
    intent_path: str = ""
    req_path: str = ""
    # Coverage simulation result fields (populated by update_gaps_from_coverage)
    covered_labels: list[str] = field(default_factory=list)
    missed_labels: list[str] = field(default_factory=list)
    uncovered_labels: list[str] = field(default_factory=list)
    coverage_pass: int = 0  # 0 = no coverage data applied; N = pass number


def analyse_gaps(
    ir: IR,
    intent_result,
    req_result,
    coverage_labels: list[dict],
) -> GapReport:
    """Perform bidirectional gap analysis between requirements and coverage labels.

    Direction A (ERROR): Each requirement in req_result that is not waived and
    has no matching coverage label with the same req_id generates an error entry.

    Direction B (WARNING): Each coverage label with source != "inferred" and
    req_id == None and not waived generates a warning entry. Inferred entries
    (Tier 3) never produce warnings.

    Waivers: Waived requirements and coverage labels with waived=True are
    collected into the waivers list.

    Args:
        ir: Parsed design intermediate representation.
        intent_result: IntentParseResult | None — parsed intent file result.
        req_result: ReqParseResult | None — parsed requirements file result.
        coverage_labels: List of coverage label dicts from _build_coverage_labels.

    Returns:
        GapReport with errors, warnings, and waivers populated.
    """
    report = GapReport(
        design_name=ir.design_name,
        coverage_labels=coverage_labels,
        req_result=req_result,
        intent_result=intent_result,
    )

    # Build index of req_ids present in coverage_labels
    covered_req_ids: set[str] = set()
    for lbl in coverage_labels:
        if lbl.get("req_id") is not None:
            covered_req_ids.add(lbl["req_id"])

    # Direction A: requirements not covered by any PSS label.
    # Source priority: .req file > inline requirements in .intent file.
    if req_result is not None and hasattr(req_result, "requirements"):
        for req_id, req_detail in req_result.requirements.items():
            if req_detail.get("waived"):
                # Collect waiver entry
                report.waivers.append({
                    "req_id": req_id,
                    "statement": req_detail.get("statement", ""),
                    "waiver_reason": req_detail.get("waiver_reason", ""),
                    "source": "requirement",
                })
            else:
                if req_id not in covered_req_ids:
                    report.errors.append({
                        "req_id": req_id,
                        "message": (
                            f"Requirement '{req_id}' has no corresponding PSS coverage label."
                        ),
                        "statement": req_detail.get("statement", ""),
                    })
    elif req_result is None and intent_result is not None:
        # No .req file — use inline requirements from [requirements] section of .intent.
        # These are the stepping-stone requirements before promotion to a .req file.
        inline_reqs = getattr(intent_result, "inline_requirements", {})
        for req_id, req_detail in inline_reqs.items():
            if req_detail.get("waived"):
                report.waivers.append({
                    "req_id": req_id,
                    "statement": req_detail.get("statement", ""),
                    "waiver_reason": req_detail.get("waiver_reason", ""),
                    "source": "intent-inline",
                })
            else:
                if req_id not in covered_req_ids:
                    report.errors.append({
                        "req_id": req_id,
                        "message": (
                            f"Requirement '{req_id}' (intent-inline) has no"
                            f" corresponding PSS coverage label."
                        ),
                        "statement": req_detail.get("statement", ""),
                        "source": "intent-inline",
                    })

    # Direction B: coverage labels from intent/req with no req_id
    for lbl in coverage_labels:
        if lbl.get("source") == "inferred":
            # Inferred entries never generate warnings
            continue
        if lbl.get("req_id") is None and not lbl.get("waived"):
            report.warnings.append({
                "label": lbl["label"],
                "display": lbl["display"],
                "source": lbl["source"],
                "message": (
                    f"Coverage label '{lbl['label']}' ({lbl['display']}) "
                    f"has no traceable requirement ID."
                ),
            })

    # Collect waived coverage labels
    for lbl in coverage_labels:
        if lbl.get("waived"):
            report.waivers.append({
                "req_id": lbl.get("req_id"),
                "label": lbl["label"],
                "display": lbl["display"],
                "waiver_reason": lbl.get("waiver_reason", ""),
                "source": "coverage_label",
            })

    return report


def update_gaps_from_coverage(
    report: GapReport,
    coverage: CoverageResult,
) -> GapReport:
    """Update gap report with simulation coverage data.

    Marks each coverage label as hit, missed, or unknown based on the
    ``CoverageResult``. Removes errors whose requirement is now fully
    covered. Removes warnings whose label is now fully hit. Waiver
    entries are preserved unchanged.

    Args:
        report: Existing GapReport produced by :func:`analyse_gaps`.
        coverage: Coverage data from :func:`~agents.coverage_reader.read_coverage_xml`.

    Returns:
        The same ``report`` object with ``covered_labels``, ``missed_labels``,
        ``uncovered_labels`` populated and ``errors``/``warnings`` pruned.
    """
    # Reset coverage tracking lists (idempotent if called multiple times)
    report.covered_labels = []
    report.missed_labels = []
    report.uncovered_labels = []

    # Classify every known coverage label
    covered_set: set[str] = set()
    missed_set: set[str] = set()

    for lbl in report.coverage_labels:
        label_name: str = lbl["label"]
        if label_name in coverage.covergroups:
            if coverage.covergroups[label_name]:
                report.covered_labels.append(label_name)
                covered_set.add(label_name)
            else:
                report.missed_labels.append(label_name)
                missed_set.add(label_name)
        else:
            report.uncovered_labels.append(label_name)

    # Build set of req_ids whose labels are now covered
    covered_req_ids: set[str] = set()
    for lbl in report.coverage_labels:
        if lbl["label"] in covered_set and lbl.get("req_id"):
            covered_req_ids.add(lbl["req_id"])

    # Prune errors for fully-covered requirements
    report.errors = [
        e for e in report.errors
        if e.get("req_id") not in covered_req_ids
    ]

    # Prune warnings for labels that are now hit
    report.warnings = [
        w for w in report.warnings
        if w.get("label") not in covered_set
    ]

    return report


def write_gap_report(report: GapReport, out_path: str) -> str:
    """Write a formatted gap report to a file.

    Args:
        report: GapReport produced by analyse_gaps.
        out_path: Destination file path for the report.

    Returns:
        The out_path that was written.
    """
    lines: list[str] = []
    today = date.today().isoformat()

    lines.append("=" * 72)
    lines.append(f"pssgen Gap Report — {report.design_name}")
    lines.append(f"Generated: {today}")
    if report.input_file:
        lines.append(f"Input:     {report.input_file}")
    if report.intent_path:
        lines.append(f"Intent:    {report.intent_path}")
    if report.req_path:
        lines.append(f"Reqs:      {report.req_path}")
    req_mode = getattr(report.req_result, "mode", None)
    if req_mode is not None:
        lines.append(f"Req mode:  {req_mode}")
    else:
        lines.append("Req mode:  none (no .req file — Direction A skipped)")
    lines.append("=" * 72)
    lines.append("")

    # Summary line
    lines.append(
        f"Summary: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s), "
        f"{len(report.waivers)} waived"
    )
    lines.append("")

    # ERRORS section
    lines.append("ERRORS (requirements without PSS coverage labels):")
    if report.errors:
        for entry in report.errors:
            lines.append(
                f"  [ERROR] {entry['req_id']}: {entry['message']}"
            )
            if entry.get("statement"):
                lines.append(f"    Statement: {entry['statement']}")
    else:
        lines.append("  (none)")
    lines.append("")

    # WARNINGS section
    lines.append("WARNINGS (PSS labels without traceable requirement IDs):")
    if report.warnings:
        for entry in report.warnings:
            lines.append(f"  [WARNING] {entry['message']}")
    else:
        lines.append("  (none)")
    lines.append("")

    # WAIVERS section
    lines.append("WAIVERS:")
    if report.waivers:
        for entry in report.waivers:
            req_id = entry.get("req_id") or entry.get("label", "?")
            reason = entry.get("waiver_reason") or "(no reason)"
            lines.append(f"  [WAIVED] {req_id}: {reason}")
    else:
        lines.append("  (none)")
    lines.append("")

    # Coverage labels section
    lines.append("COVERAGE LABELS:")
    if report.coverage_labels:
        for lbl in report.coverage_labels:
            waived_tag = " [WAIVED]" if lbl.get("waived") else ""
            req_tag = f" → {lbl['req_id']}" if lbl.get("req_id") else ""
            lines.append(
                f"  {lbl['label']}  [{lbl['source']}]{req_tag}{waived_tag}"
            )
    else:
        lines.append("  (none)")
    lines.append("")

    # COVERAGE STATUS section — only when coverage data was applied
    has_coverage = (
        report.covered_labels
        or report.missed_labels
        or report.uncovered_labels
    )
    if has_coverage:
        pass_label = (
            f"from simulation pass {report.coverage_pass}"
            if report.coverage_pass > 0
            else "from simulation"
        )
        lines.append(f"COVERAGE STATUS ({pass_label}):")
        lines.append("─" * 41)

        # Build display-name lookup from coverage_labels
        display_map: dict[str, str] = {
            lbl["label"]: lbl.get("display", lbl["label"])
            for lbl in report.coverage_labels
        }

        for name in report.covered_labels:
            display = display_map.get(name, name)
            lines.append(f"  HIT     {name}   ({display} covered)")
        for name in report.missed_labels:
            display = display_map.get(name, name)
            lines.append(f"  MISSED  {name}   (add more sequences)")
        for name in report.uncovered_labels:
            display = display_map.get(name, name)
            lines.append(f"  UNKNOWN {name}   (not in coverage XML)")
        lines.append("")

    lines.append("=" * 72)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return out_path


def format_console_summary(report: GapReport) -> str:
    """Return a single-line console summary of gap counts.

    Args:
        report: GapReport produced by analyse_gaps.

    Returns:
        Formatted summary string.
    """
    return (
        f"[pssgen] Gap report: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s), "
        f"{len(report.waivers)} waived"
    )
