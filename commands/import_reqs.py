# ===========================================================
# FILE:         commands/import_reqs.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Implements the "pssgen import-reqs" subcommand. Reads a Word .docx
#   requirements document (or other supported format), extracts requirement
#   statements and verification methods, and writes a .req bootstrap file
#   in the standard pssgen format for engineer review. Never overwrites an
#   existing .req file — the engineer owns it from the moment it is created.
#
# LAYER:        Entry point (above all pipeline layers)
# PHASE:        v5a
#
# FUNCTIONS:
#   run_import_reqs(args)
#     Parse source document, write .req bootstrap, print summary.
#     Returns 0 on success, 1 on error.
#
# DEPENDENCIES:
#   Standard library:  os, sys, tomllib
#   Internal:          parser.docx_req_parser, config
#
# HISTORY:
#   v5a   2026-04-07  SB  Initial implementation; Word .docx extraction path
#
# ===========================================================
"""commands/import_reqs.py — import-reqs subcommand implementation.

Phase: v5a
Layer: Entry point (above all pipeline layers)

Reads a source requirements document and writes a .req bootstrap file
for engineer review. The .req file is never overwritten once created.
"""
import os
import sys
import tomllib
from datetime import date

from config import find_project_config
from parser.docx_req_parser import parse_docx_requirements


def _read_toml_raw(toml_path: str) -> dict:
    """Load a TOML file and return the raw dict.

    Args:
        toml_path: Absolute path to the TOML file.

    Returns:
        Raw dict from tomllib, or empty dict on error.
    """
    try:
        with open(toml_path, "rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def run_import_reqs(args) -> int:
    """Execute the import-reqs subcommand.

    Determines the source document path from CLI args or pssgen.toml,
    calls the appropriate parser, writes a .req bootstrap file, and
    prints a user-facing summary. Never overwrites an existing .req file.

    Args:
        args: Parsed argument namespace with attributes:
            source (str | None): Path to the source document.
            output (str | None): Explicit output .req file path.
            from_format (str): Source format — currently only "word".

    Returns:
        0 on success, 1 on any error.
    """
    from_format = getattr(args, "from_format", "word")
    if from_format != "word":
        print(
            f"[pssgen] ERROR: Unsupported format: {from_format!r}. Only 'word' is supported.",
            file=sys.stderr,
        )
        return 1

    # ------------------------------------------------------------------
    # (a) Determine source path and design name
    # ------------------------------------------------------------------
    source_path: str | None = getattr(args, "source", None)
    design_name: str | None = None
    toml_dir: str | None = None
    toml_hdl_stem: str | None = None

    # Always search for pssgen.toml for project context
    search_start = (
        os.path.dirname(os.path.abspath(source_path))
        if source_path
        else (getattr(args, "output_dir", None) or os.getcwd())
    )
    toml_path = find_project_config(search_start)

    if toml_path:
        toml_dir = os.path.dirname(os.path.abspath(toml_path))
        raw_toml = _read_toml_raw(toml_path)

        # Extract design name from [project] name
        project_sec = raw_toml.get("project", {})
        design_name = project_sec.get("name")

        # Extract requirements source from [requirements] source
        if not source_path:
            req_sec = raw_toml.get("requirements", {})
            rel_source = req_sec.get("source")
            if rel_source:
                source_path = os.path.join(toml_dir, rel_source)

        # Extract HDL stem from [[sources]] for output path derivation
        sources_list = raw_toml.get("sources")
        if isinstance(sources_list, list) and sources_list:
            first_hdl = sources_list[0].get("hdl", "")
            if first_hdl:
                toml_hdl_stem = os.path.splitext(os.path.basename(first_hdl))[0]

    if not source_path:
        print(
            "[pssgen] ERROR: No source document specified.\n"
            "         Provide a path or set [requirements] source in pssgen.toml.",
            file=sys.stderr,
        )
        return 1

    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        print(f"[pssgen] ERROR: Source document not found: {source_path}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # (b) Determine output path
    # ------------------------------------------------------------------
    output_path: str | None = getattr(args, "output", None)

    if not output_path:
        if design_name and toml_dir:
            # Place .req next to the pssgen.toml (project root)
            output_path = os.path.join(toml_dir, f"{design_name}.req")
        else:
            # Fall back: use source document stem, place alongside source
            stem = os.path.splitext(os.path.basename(source_path))[0]
            output_path = os.path.join(os.path.dirname(source_path), f"{stem}.req")

    output_path = os.path.abspath(output_path)

    # ------------------------------------------------------------------
    # (c) Never overwrite an existing .req file
    # ------------------------------------------------------------------
    if os.path.exists(output_path):
        print(f"[pssgen] .req file already exists: {output_path}")
        print("[pssgen] Delete it manually to re-extract.")
        return 1

    # ------------------------------------------------------------------
    # (d) Parse the source document
    # ------------------------------------------------------------------
    try:
        result = parse_docx_requirements(source_path)
    except FileNotFoundError:
        print(f"[pssgen] ERROR: File not found: {source_path}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[pssgen] ERROR: Failed to parse {source_path}: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # (e) Write the .req bootstrap file
    # ------------------------------------------------------------------
    if not design_name:
        design_name = os.path.splitext(os.path.basename(source_path))[0]

    source_filename = os.path.basename(source_path)
    extraction_date = date.today().strftime("%Y-%m-%d")

    lines: list[str] = []

    # Header block
    lines.append(f"# requirements: {design_name}")
    lines.append(f"# extracted from: {source_filename}")
    lines.append(f"# extraction date: {extraction_date}")
    lines.append("# mode: campaign")
    lines.append("# NOTE: Never overwritten by pssgen.")
    lines.append("# NOTE: Verification methods pre-populated from VCRM.")
    lines.append("# NOTE: Review all entries. Change [GENERATED] to")
    lines.append("#       [CONFIRMED] when verified. Add [WAIVED] with")
    lines.append("#       rationale for out-of-scope requirements.")
    lines.append("# NOTE: UART-BR-004 is the gap demo requirement.")
    lines.append("#       Leave it as [GENERATED] for the initial demo.")
    lines.append("#       The gap report will fire a Direction A ERROR.")
    lines.append("#       Add coverage cross-reference in .intent to close.")

    # Requirement entries — document order
    for req_id in result.req_ids:
        entry = result.requirements[req_id]
        lines.append("")  # blank line separator

        # ID + statement on one line
        lines.append(f"[{req_id}] {entry['statement']}")

        # Verification method
        verification = entry.get("verification") or []
        if verification:
            lines.append(f"  verification: {', '.join(verification)}")
        else:
            lines.append("  verification: (pending review)")

        # Disposition
        lines.append("  [GENERATED]")

    content = "\n".join(lines) + "\n"

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        print(f"[pssgen] ERROR: Cannot write {output_path}: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # (f) Print summary
    # ------------------------------------------------------------------
    n = len(result.requirements)
    print(f"[pssgen] import-reqs: extracted {n} requirements")
    print("[pssgen] Verification methods pre-populated from VCRM.")
    print(f"[pssgen] Output: {output_path}")
    print(
        f"[pssgen] Next: review {output_path}, then run pssgen\n"
        "         to generate the gap report."
    )
    return 0
