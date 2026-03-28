# ===========================================================
# FILE:         parser/intent_parser.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Parses .intent files containing structured natural language verification
#   intent. Extracts section headings, requirement IDs, requirement scheme
#   prefixes, and waiver entries. Disposition keywords (GENERATED, CONFIRMED,
#   WAIVED) are explicitly excluded from requirement ID extraction.
#
# LAYER:        1 — parser
# PHASE:        v3a
#
# FUNCTIONS:
#   parse_intent(intent_file)
#     Parse a .intent file and return an IntentParseResult.
#
# DEPENDENCIES:
#   Standard library:  re, dataclasses, typing
#   Internal:          none
#
# HISTORY:
#   v3a   2026-03-28  SB  Initial implementation; section, req ID, scheme, and waiver extraction
#
# ===========================================================
"""parser/intent_parser.py — Structured natural language intent file parser.

Phase: v3a
Layer: 1 (parser)

Parses .intent files, extracting sections, requirement IDs, requirement
schemes, and waivers. Requirement ID detection uses regex pattern matching;
disposition keywords are explicitly excluded from ID extraction.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


# Disposition keywords that must NOT be treated as requirement IDs
_DISPOSITION_KEYWORDS = {"GENERATED", "CONFIRMED", "WAIVED"}

# Requirement ID pattern: [ALPHA(-ALPHANUM)+] with at least two dash-separated segments.
# Segments after the first may start with a digit (e.g. -047 in SYS-REQ-047).
_REQ_ID_PATTERN = re.compile(r'\[([A-Z][A-Z0-9]*(?:-[A-Z0-9][A-Z0-9]*){1,4})\]')


@dataclass
class IntentParseResult:
    """Result of parsing a structured natural language intent file.

    Attributes:
        sections: Mapping of section heading to list of content lines.
        req_ids: All requirement IDs found in the file.
        req_schemes: Unique requirement scheme prefixes, e.g. ["SYS-REQ"].
        waivers: List of waiver records with item, reason, and req_ids keys.
    """
    sections: dict[str, list[str]] = field(default_factory=dict)
    req_ids: list[str] = field(default_factory=list)
    req_schemes: list[str] = field(default_factory=list)
    waivers: list[dict] = field(default_factory=list)


def _extract_req_ids(text: str) -> list[str]:
    """Extract requirement IDs from a text string.

    Filters out disposition keywords (GENERATED, CONFIRMED, WAIVED).

    Args:
        text: Input text to scan for bracketed requirement IDs.

    Returns:
        List of requirement ID strings without surrounding brackets.
    """
    ids = []
    for match in _REQ_ID_PATTERN.finditer(text):
        candidate = match.group(1)
        if candidate not in _DISPOSITION_KEYWORDS:
            ids.append(candidate)
    return ids


def _derive_scheme(req_id: str) -> Optional[str]:
    """Derive the requirement scheme prefix from a requirement ID.

    The scheme is everything except the last dash-separated segment.
    For example, "SYS-REQ-047" yields "SYS-REQ".

    Args:
        req_id: A requirement ID such as "SYS-REQ-047".

    Returns:
        The scheme prefix string, or None if the ID has only one segment.
    """
    parts = req_id.split("-")
    if len(parts) < 2:
        return None
    return "-".join(parts[:-1])


def parse_intent(intent_file: str) -> IntentParseResult:
    """Parse a structured natural language intent file.

    Extracts disposition-tagged entries, requirement IDs,
    waivers, and section content. Detects requirement ID
    schemes automatically using regex pattern matching.

    Args:
        intent_file: Path to .intent file.

    Returns:
        IntentParseResult with sections, req_ids,
        req_schemes, and waivers.

    Raises:
        FileNotFoundError: If intent_file does not exist.
        OSError: If the file cannot be read.
    """
    with open(intent_file, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    sections: dict[str, list[str]] = {}
    all_req_ids: list[str] = []
    waivers: list[dict] = []

    current_section: Optional[str] = None

    for line in lines:
        stripped = line.rstrip()

        # Skip comment lines and blank lines for section detection
        if stripped.startswith("#") or not stripped:
            continue

        # Section heading: a line that ends with ':' and has no leading whitespace
        # (and is not a waiver/disposition line)
        if not stripped[0].isspace() and stripped.endswith(":"):
            heading = stripped[:-1].strip()
            current_section = heading
            if heading not in sections:
                sections[heading] = []
            continue

        # Content line (may belong to current section)
        if current_section is not None:
            sections[current_section].append(stripped)

        # Waiver detection: line contains [WAIVED]
        if "[WAIVED]" in stripped:
            waiver_ids = _extract_req_ids(stripped)
            # item is the text after [WAIVED]
            waived_match = re.search(r'\[WAIVED\](.*)', stripped)
            item_text = waived_match.group(1).strip() if waived_match else stripped
            # Remove any trailing req IDs from the item text for cleanliness
            item_clean = _REQ_ID_PATTERN.sub("", item_text).strip()
            waivers.append({
                "item": item_clean,
                "reason": item_clean,
                "req_ids": waiver_ids,
            })
            continue

        # Collect requirement IDs from non-waiver lines
        line_ids = _extract_req_ids(stripped)
        all_req_ids.extend(line_ids)

    # Deduplicate IDs while preserving first-seen order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for rid in all_req_ids:
        if rid not in seen:
            seen.add(rid)
            unique_ids.append(rid)

    # Also collect IDs from waiver lines
    for waiver in waivers:
        for rid in waiver["req_ids"]:
            if rid not in seen:
                seen.add(rid)
                unique_ids.append(rid)

    # Derive unique schemes
    scheme_seen: set[str] = set()
    unique_schemes: list[str] = []
    for rid in unique_ids:
        scheme = _derive_scheme(rid)
        if scheme and scheme not in scheme_seen:
            scheme_seen.add(scheme)
            unique_schemes.append(scheme)

    return IntentParseResult(
        sections=sections,
        req_ids=unique_ids,
        req_schemes=unique_schemes,
        waivers=waivers,
    )
