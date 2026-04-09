# ===========================================================
# FILE:         agents/datasheet_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Generates or updates DATASHEET.md for an IP block from the populated
#   IR and optional intent/req parse results. Derived sections (Identity,
#   Maturity, Quick Start, Revision History) are fully regenerated on each
#   run. Engineer-entered sections (Known Limitations, Resource Utilization,
#   Power Estimate, Tested With) are extracted from an existing file and
#   preserved verbatim. A new revision row is appended only when content
#   has changed from the existing file.
#
# LAYER:        3 — agents
# PHASE:        v5a
#
# FUNCTIONS:
#   generate_datasheet(ir, intent_result, req_result, out_path,
#                      existing_path, version, author, license_str)
#     Generate or update DATASHEET.md; return out_path.
#
# DEPENDENCIES:
#   Standard library:  os, datetime, re
#   Internal:          ir
#
# HISTORY:
#   v5a   2026-04-08  SB  Initial implementation; section-aware merge,
#                          derived regeneration, preserved content (D-026)
#
# ===========================================================
"""agents/datasheet_gen.py — IP data sheet generator and updater.

Phase: v5a
Layer: 3 (agents)

Generates DATASHEET.md from IR and artifact state. Derived sections are
always regenerated. Engineer-entered sections are extracted from an existing
file and preserved across runs using a line-by-line section parser.
"""
from __future__ import annotations

import os
import re
from datetime import date
from typing import Optional

from ir import IR


# ---------------------------------------------------------------------------
# Section extraction helpers
# ---------------------------------------------------------------------------

def _extract_section_lines(content: str, heading: str) -> list[str]:
    """Extract lines belonging to a markdown section.

    Scans for ``## <heading>`` then collects lines until the next ``---``
    separator or end of file. The heading line itself is not included.

    Args:
        content: Full file content.
        heading: Section heading text (without the ``## `` prefix).

    Returns:
        List of lines (stripped of trailing newline) between the heading
        and the next ``---`` separator.
    """
    lines = content.splitlines()
    target = f"## {heading}"
    inside = False
    result: list[str] = []
    for line in lines:
        if line.strip() == target:
            inside = True
            continue
        if inside:
            if line.strip() == "---":
                break
            result.append(line)
    return result


def _extract_table_data_rows(section_lines: list[str]) -> list[str]:
    """Extract non-header, non-separator table rows from section lines.

    Args:
        section_lines: Lines from a section (heading already removed).

    Returns:
        Table data rows as raw strings, excluding the header and divider rows.
    """
    data_rows: list[str] = []
    header_seen = False
    for line in section_lines:
        stripped = line.strip()
        if not stripped or not stripped.startswith("|"):
            continue
        # Divider row: |---|---|...
        if re.match(r"^\|[-| :]+\|$", stripped):
            header_seen = True
            continue
        if not header_seen:
            # This is the header row — skip it
            header_seen = True
            continue
        data_rows.append(line)
    return data_rows


def _extract_limitations_body(section_lines: list[str]) -> list[str]:
    """Extract bullet points and the closing italic note from limitations section.

    Args:
        section_lines: Lines from the Known Limitations section.

    Returns:
        Non-empty lines (preserving blank separator lines between bullets
        and the italic closing note).
    """
    # Strip leading/trailing blank lines but keep internal structure
    stripped = []
    for line in section_lines:
        stripped.append(line)
    # Remove leading blanks
    while stripped and not stripped[0].strip():
        stripped.pop(0)
    # Remove trailing blanks
    while stripped and not stripped[-1].strip():
        stripped.pop()
    return stripped


def _count_revision_rows(section_lines: list[str]) -> int:
    """Count data rows in the Revision History table."""
    return len(_extract_table_data_rows(section_lines))


def _last_rev_number(section_lines: list[str]) -> str:
    """Return the last revision number string from the Revision History table."""
    rows = _extract_table_data_rows(section_lines)
    if not rows:
        return "0.0"
    last = rows[-1]
    # | Rev | Date | Author | Description |
    parts = [p.strip() for p in last.split("|") if p.strip()]
    return parts[0] if parts else "0.0"


def _increment_rev(rev: str) -> str:
    """Increment the minor component of a X.Y revision string.

    Args:
        rev: Revision string like "0.1" or "0.9".

    Returns:
        Incremented revision string.
    """
    parts = rev.split(".")
    if len(parts) == 2:
        try:
            return f"{parts[0]}.{int(parts[1]) + 1}"
        except ValueError:
            pass
    return rev + ".1"


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------

def _identity_section(ir: IR, version: str, author: str, license_str: str) -> str:
    """Generate the Identity section table."""
    # Status
    if ir.hdl_source and os.path.isfile(ir.hdl_source):
        status = "IN DEVELOPMENT — architecture stub"
    elif ir.hdl_source:
        status = "NOT STARTED"
    else:
        status = "NOT STARTED"

    # Bus protocol
    axi_ports = [p for p in ir.ports if p.name.startswith("s_axi_")]
    if axi_ports:
        bus = "AXI4-Lite (ARM IHI0022E), 32-bit data, 8-bit addr"
    else:
        bus = "—"

    # Spec — not stored in IR; leave as "—"
    spec = "—"

    rows = [
        ("Design Name",  ir.design_name),
        ("Spec",         spec),
        ("Version",      version),
        ("Status",       status),
        ("Author",       author),
        ("License",      license_str),
        ("Bus Protocol", bus),
    ]

    lines = ["## Identity", ""]
    lines.append("| Field        | Value                                            |")
    lines.append("|--------------|--------------------------------------------------|")
    for field_name, value in rows:
        lines.append(f"| {field_name:<12} | {value:<48} |")
    return "\n".join(lines)


def _maturity_section(
    ir: IR,
    req_result,
    today: date,
) -> str:
    """Generate the Maturity section table."""
    today_str = today.isoformat()

    def row(label: str, done: bool, date_str: str = "") -> str:
        status = "✓ Complete" if done else "Pending"
        dt = date_str if done else "—"
        return f"| {label:<32} | {status:<10} | {dt:<10} |"

    # Requirements
    req_count = 0
    has_reqs = False
    if req_result is not None:
        try:
            req_count = len(req_result.requirements)
            has_reqs = req_count > 0
        except AttributeError:
            pass

    # Register map
    has_regmap = (
        ir.register_map is not None
        and len(ir.register_map.get("registers", [])) > 0
    )

    # VHDL entity
    has_vhdl = ir.hdl_language == "vhdl" and bool(ir.hdl_source)

    # SV stub — look for .sv alongside the .vhd
    has_sv = False
    if ir.hdl_source:
        stem = os.path.splitext(ir.hdl_source)[0]
        has_sv = os.path.isfile(stem + ".sv")

    vcrm_label = f"VCRM — {req_count} requirements" if has_reqs else "VCRM"

    lines = ["## Maturity", ""]
    lines.append("| Milestone                        | Status     | Date       |")
    lines.append("|----------------------------------|------------|------------|")
    lines.append(row("Requirements specification",            has_reqs,    today_str))
    lines.append(row(vcrm_label,                              has_reqs,    today_str))
    lines.append(row("Register map spreadsheet",              has_regmap,  today_str))
    lines.append(row("VHDL entity + architecture stub",       has_vhdl,    today_str))
    lines.append(row("SystemVerilog module + stub",           has_sv,      today_str))
    lines.append(row("Architecture implementation",           False))
    lines.append(row("pssgen gap report — all closed",        False))
    lines.append(row("Simulation — block level",              False))
    lines.append(row("Synthesis — Vivado WebPACK",            False))
    lines.append(row("Synthesis — Yosys + nextpnr",           False))
    lines.append(row("Board bring-up — ZUBoard 1CG",          False))
    lines.append(row("Board bring-up — Basys 3",              False))
    return "\n".join(lines)


def _quickstart_section(ir: IR) -> str:
    """Generate the Quick Start instantiation section."""
    # Generic map
    generic_lines: list[str] = []
    if ir.parameters:
        for name, val in ir.parameters.items():
            generic_lines.append(f"    {name:<22} => {val},")
        # Remove trailing comma from last entry
        if generic_lines:
            generic_lines[-1] = generic_lines[-1].rstrip(",")

    # Port map — derive RHS signal name
    port_lines: list[str] = []
    for port in ir.ports:
        n = port.name
        nl = n.lower()
        if nl in ("clk", "clock", "axi_aclk", "clk_i", "sys_clk"):
            rhs = "clk_s"
        elif nl in ("rst_n", "reset_n", "aresetn", "axi_aresetn", "nreset"):
            rhs = "resetn_s"
        elif nl in ("rst", "reset", "rst_i"):
            rhs = "reset_s"
        else:
            rhs = f"{n}_s"
        port_lines.append(f"    {n:<18} => {rhs},")
    if port_lines:
        port_lines[-1] = port_lines[-1].rstrip(",")

    lines: list[str] = []
    lines.append("## Quick Start")
    lines.append("")

    if ir.hdl_language in ("vhdl", None, ""):
        lines.append("VHDL instantiation at default generics:")
        lines.append("```vhdl")
        lines.append(f"u_{ir.design_name} : entity work.{ir.design_name}")
        if generic_lines:
            lines.append("  generic map (")
            lines.extend(generic_lines)
            lines.append("  )")
        lines.append("  port map (")
        lines.extend(port_lines)
        lines.append("  );")
        lines.append("```")
    else:
        # SystemVerilog
        lines.append("SystemVerilog instantiation:")
        lines.append("```systemverilog")
        lines.append(f"{ir.design_name} u_{ir.design_name} (")
        lines.extend(port_lines)
        lines.append(");")
        lines.append("```")

    lines.append("")
    lines.append(
        "See BALU-RS-001 Section 3 for generic ranges and constraints."
    )
    lines.append(
        "See the register map spreadsheet for the complete field list."
    )
    return "\n".join(lines)


def _limitations_section(body_lines: list[str]) -> str:
    """Generate the Known Limitations section with preserved body."""
    lines = ["## Known Limitations and Integration Notes", ""]
    lines.extend(body_lines)
    return "\n".join(lines)


_DEFAULT_LIMITATIONS = [
    "- No known limitations at this stage.",
    "",
    "*This section grows as integration experience accumulates.*",
]


def _resource_section(data_rows: list[str]) -> str:
    """Generate the Resource Utilization section."""
    lines = [
        "## Resource Utilization",
        "",
        "Add a row each time synthesis is run on a new target.",
        'Fmax is post-route worst-case at the stated speed grade.',
        'RAM Blocks cell specifies vendor type (e.g. "2 BRAM36",',
        '"1 M10K", "3 EBR"). LUTs/ALMs uses vendor-appropriate term.',
        "",
        "| Target Device | Tool | LUTs/ALMs | FFs | RAM Blocks | DSP | Fmax (MHz) | Notes | Date |",
        "|---------------|------|-----------|-----|------------|-----|------------|-------|------|",
    ]
    lines.extend(data_rows)
    return "\n".join(lines)


def _power_section(data_rows: list[str]) -> str:
    """Generate the Power Estimate section."""
    lines = [
        "## Power Estimate",
        "",
        "Add a row each time a power analysis is run.",
        "Dynamic and static power at typical conditions unless noted.",
        "",
        "| Target Device | Tool | Dynamic (mW) | Static (mW) | Notes | Date |",
        "|---------------|------|-------------|-------------|-------|------|",
    ]
    lines.extend(data_rows)
    return "\n".join(lines)


_DEFAULT_TESTED_ROWS = [
    "| pssgen  | v5a     | Verification artifact generation  |",
    "| Vivado  | —       | Pending first synthesis run       |",
    "| GHDL    | —       | Pending simulation                |",
    "| Questa  | —       | UVM simulation target             |",
    "| Yosys   | —       | Pending synthesis run             |",
]


def _tested_section(data_rows: list[str]) -> str:
    """Generate the Tested With section."""
    lines = [
        "## Tested With",
        "",
        "| Item    | Version | Notes                             |",
        "|---------|---------|-----------------------------------|",
    ]
    if data_rows:
        lines.extend(data_rows)
    else:
        lines.extend(_DEFAULT_TESTED_ROWS)
    return "\n".join(lines)


def _revision_section(existing_rows: list[str], new_row: Optional[str]) -> str:
    """Generate the Revision History section."""
    lines = [
        "## Revision History",
        "",
        "| Rev | Date       | Author    | Description                  |",
        "|-----|------------|-----------|------------------------------|",
    ]
    lines.extend(existing_rows)
    if new_row:
        lines.append(new_row)
    return "\n".join(lines)


_DEFAULT_REVISION_ROWS = [
    "| 0.1 | 2026-04-07 | S. Belton | Initial — stub phase         |",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_datasheet(
    ir: IR,
    intent_result=None,
    req_result=None,
    out_path: str = "DATASHEET.md",
    existing_path: Optional[str] = None,
    version: str = "0.1.0",
    author: str = "S. Belton, BelTech Systems LLC",
    license_str: str = "MIT",
) -> str:
    """Generate or update DATASHEET.md for an IP block.

    Reads existing_path if provided to extract preserved sections.
    Derives all other content from ir, intent_result, and req_result.
    Writes the merged result to out_path. Returns out_path.

    Args:
        ir: Populated IR instance.
        intent_result: IntentParseResult or None.
        req_result: ReqParseResult or None.
        out_path: Destination path for the generated DATASHEET.md.
        existing_path: Path to an existing DATASHEET.md to read preserved
            content from. None means generate from scratch.
        version: IP version string for the Identity table.
        author: Author string for the Identity table.
        license_str: License name for the Identity table.

    Returns:
        out_path after writing.
    """
    today = date.today()
    existing_content: Optional[str] = None

    if existing_path and os.path.isfile(existing_path):
        with open(existing_path, encoding="utf-8") as fh:
            existing_content = fh.read()

    # --- Extract preserved content from existing file ---
    if existing_content:
        limitations_lines = _extract_section_lines(
            existing_content, "Known Limitations and Integration Notes"
        )
        limitations_body = _extract_limitations_body(limitations_lines)

        resource_section_lines = _extract_section_lines(
            existing_content, "Resource Utilization"
        )
        resource_rows = _extract_table_data_rows(resource_section_lines)

        power_section_lines = _extract_section_lines(
            existing_content, "Power Estimate"
        )
        power_rows = _extract_table_data_rows(power_section_lines)

        tested_section_lines = _extract_section_lines(
            existing_content, "Tested With"
        )
        tested_rows = _extract_table_data_rows(tested_section_lines)

        revision_section_lines = _extract_section_lines(
            existing_content, "Revision History"
        )
        revision_rows = _extract_table_data_rows(revision_section_lines)
    else:
        limitations_body = list(_DEFAULT_LIMITATIONS)
        resource_rows = []
        power_rows = []
        tested_rows = list(_DEFAULT_TESTED_ROWS)
        revision_rows = list(_DEFAULT_REVISION_ROWS)
        revision_section_lines = []

    # --- Generate all derived sections ---
    identity = _identity_section(ir, version, author, license_str)
    maturity = _maturity_section(ir, req_result, today)
    quickstart = _quickstart_section(ir)

    # --- Assemble content WITHOUT revision row addition first ---
    def _assemble(rev_rows: list[str], extra_row: Optional[str]) -> str:
        sections = [
            f"# IP Data Sheet: {ir.design_name}",
            "",
            identity,
            "",
            "---",
            "",
            maturity,
            "",
            "---",
            "",
            quickstart,
            "",
            "---",
            "",
            _limitations_section(limitations_body),
            "",
            "---",
            "",
            _resource_section(resource_rows),
            "",
            "---",
            "",
            _power_section(power_rows),
            "",
            "---",
            "",
            _tested_section(tested_rows),
            "",
            "---",
            "",
            _revision_section(rev_rows, extra_row),
        ]
        return "\n".join(sections) + "\n"

    # First pass: generate without new rev row
    draft = _assemble(revision_rows, None)

    # --- Determine if a new revision row is needed ---
    new_rev_row: Optional[str] = None
    if existing_content is not None:
        # Strip the revision section from both for comparison
        def _strip_revision(text: str) -> str:
            idx = text.find("## Revision History")
            return text[:idx] if idx >= 0 else text

        if _strip_revision(draft) != _strip_revision(existing_content):
            last_rev = _last_rev_number(revision_section_lines) if existing_content else "0.1"
            next_rev = _increment_rev(last_rev)
            short_author = author.split(",")[0].strip()
            new_rev_row = (
                f"| {next_rev} | {today.isoformat()} | {short_author:<9} |"
                " Auto-updated — maturity status      |"
            )
    # else: no existing file — no new row to append (revision_rows already has defaults)

    final = _assemble(revision_rows, new_rev_row)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(final)

    return out_path
