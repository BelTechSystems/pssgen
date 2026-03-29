# ===========================================================
# FILE:         agents/coverage_reader.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Reads Vivado XML coverage output and extracts covergroup hit/miss
#   information keyed by covergroup name. Gracefully degrades on missing
#   or malformed XML — coverage read failure is always non-fatal. A
#   fallback path handles Vivado version differences in XML structure.
#
# LAYER:        3 — agents
# PHASE:        v3c-b
#
# FUNCTIONS:
#   read_coverage_xml(xml_path)
#     Parse a Vivado coverage XML file; return CoverageResult with hit/miss.
#
# DEPENDENCIES:
#   Standard library:  dataclasses, os, xml.etree.ElementTree
#   Internal:          (none)
#
# HISTORY:
#   v3c-b  2026-03-29  SB  Initial implementation; Vivado XML coverage reader
#
# ===========================================================
"""agents/coverage_reader.py — Vivado XML coverage database reader.

Phase: v3c-b
Layer: 3 (agents)

Parses Vivado coverage XML files to extract covergroup hit/miss status.
Returns a CoverageResult dataclass; never raises — all errors become
non-fatal parse_warnings.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CoverageResult:
    """Result of reading a Vivado XML coverage file.

    Attributes:
        covergroups: Mapping of covergroup_name → True (hit) / False (missed).
            A covergroup is considered "hit" when its coverage_pct >= 100.0.
        source_file: Absolute path to the XML file that was read.
        parse_warnings: Non-fatal issues encountered during parsing.
            Populated when the file is missing, malformed, or uses an
            unexpected XML structure.
    """
    covergroups: dict[str, bool] = field(default_factory=dict)
    source_file: str = ""
    parse_warnings: list[str] = field(default_factory=list)


def read_coverage_xml(xml_path: str) -> CoverageResult:
    """Read a Vivado XML coverage database file.

    Extracts covergroup names and their hit/miss status. The primary parse
    path expects the standard Vivado structure::

        <coverage>
          <covergroups>
            <covergroup name="cg_NAME" ...>
              <coverage_pct>100.0</coverage_pct>
            </covergroup>
          </covergroups>
        </coverage>

    If the primary structure is not found, falls back to searching for any
    XML element with a ``name`` attribute starting with ``cg_`` and a
    numeric child element value. A ``parse_warning`` is added when the
    fallback path is used.

    Gracefully handles missing or malformed XML by returning an empty
    ``CoverageResult`` with a descriptive ``parse_warning``.

    Args:
        xml_path: Path to the Vivado coverage XML file.

    Returns:
        ``CoverageResult`` with ``covergroups`` populated. On error,
        ``covergroups`` is empty and ``parse_warnings`` describes the issue.
    """
    result = CoverageResult(source_file=xml_path)

    if not os.path.isfile(xml_path):
        result.parse_warnings.append(
            f"Coverage XML file not found: {xml_path}"
        )
        return result

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        result.parse_warnings.append(
            f"Failed to parse coverage XML '{xml_path}': {exc}"
        )
        return result

    # -------------------------------------------------------------------
    # Primary parse: covergroup elements inside a <covergroups> container
    # -------------------------------------------------------------------
    cg_elements = root.findall(".//covergroups/covergroup")
    if cg_elements:
        for cg in cg_elements:
            name = cg.get("name")
            if not name:
                continue
            pct_el = cg.find("coverage_pct")
            if pct_el is not None and pct_el.text:
                try:
                    pct = float(pct_el.text.strip())
                    result.covergroups[name] = pct >= 100.0
                except ValueError:
                    result.parse_warnings.append(
                        f"Non-numeric coverage_pct for '{name}': "
                        f"{pct_el.text!r} — skipping"
                    )
        return result

    # -------------------------------------------------------------------
    # Fallback: search the entire tree for elements whose "name" attribute
    # begins with "cg_" and has any numeric child text value.
    # -------------------------------------------------------------------
    for elem in root.iter():
        name: Optional[str] = elem.get("name")
        if not name or not name.startswith("cg_"):
            continue
        for child in elem:
            if child.text:
                try:
                    val = float(child.text.strip())
                    result.covergroups[name] = val >= 100.0
                    break
                except ValueError:
                    pass

    result.parse_warnings.append(
        "Primary <covergroups>/<covergroup> XML structure not found; "
        "used element-name fallback search. Results may be incomplete "
        "if the Vivado XML format differs from the expected structure."
    )
    return result
