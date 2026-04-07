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
#   prefixes, waiver entries, and inline requirements from an optional
#   [requirements] section. Disposition keywords (GENERATED, CONFIRMED,
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
#   Standard library:  re, sys, dataclasses, typing
#   Internal:          none
#
# HISTORY:
#   v3a      2026-03-28  SB  Initial implementation; section, req ID, scheme, and waiver extraction
#   v5a-prep 2026-04-06  SB  inline_requirements from [requirements] section; waiver-location warning (D-025)
#
# ===========================================================
"""parser/intent_parser.py — Structured natural language intent file parser.

Phase: v3a
Layer: 1 (parser)

Parses .intent files, extracting sections, requirement IDs, requirement
schemes, waivers, and inline requirements. Requirement ID detection uses
regex pattern matching; disposition keywords are explicitly excluded.
"""
import re
import sys
from dataclasses import dataclass, field
from typing import Optional


# Disposition keywords that must NOT be treated as requirement IDs
_DISPOSITION_KEYWORDS = {"GENERATED", "CONFIRMED", "WAIVED"}

# Requirement ID pattern: [ALPHA(-ALPHANUM)+] with at least two dash-separated segments.
# Segments after the first may start with a digit (e.g. -047 in SYS-REQ-047).
_REQ_ID_PATTERN = re.compile(r'\[([A-Z][A-Z0-9]*(?:-[A-Z0-9][A-Z0-9]*){1,4})\]')

# Pattern for bare (unbracketed) requirement ID-like strings used in waiver warnings.
# Requires three dash-separated segments where the last is numeric: SYS-REQ-001.
_WAIVER_REQ_WARN_PATTERN = re.compile(
    r'[A-Z][A-Z0-9]*-[A-Z0-9][A-Z0-9]*-[0-9]+'
)

# Pattern to match a requirement entry line in the [requirements] section.
_REQ_INLINE_ENTRY_PATTERN = re.compile(
    r'^\s*\[([A-Z][A-Z0-9]*(?:-[A-Z0-9][A-Z0-9]*){1,4})\]\s*(.*)'
)


@dataclass
class IntentParseResult:
    """Result of parsing a structured natural language intent file.

    Attributes:
        sections: Mapping of section heading to list of content lines.
        req_ids: All requirement IDs found in the file.
        req_schemes: Unique requirement scheme prefixes, e.g. ["SYS-REQ"].
        waivers: List of waiver records with item, reason, and req_ids keys.
        inline_requirements: Requirements parsed from the [requirements] section,
            keyed by requirement ID. Each entry has the same structure as
            ReqParseResult.requirements entries (statement, verification, waived,
            waiver_reason). Empty dict when no [requirements] section is present.
    """
    sections: dict[str, list[str]] = field(default_factory=dict)
    req_ids: list[str] = field(default_factory=list)
    req_schemes: list[str] = field(default_factory=list)
    waivers: list[dict] = field(default_factory=list)
    inline_requirements: dict[str, dict] = field(default_factory=dict)


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


def _parse_inline_requirements(lines: list[str]) -> dict[str, dict]:
    """Parse requirement entries from the [requirements] section of an intent file.

    Applies the same entry format as .req files: each entry begins with a
    bracketed requirement ID line, optionally followed by indented
    ``verification:`` and ``[WAIVED]`` lines.

    Args:
        lines: Content lines from the ``requirements`` section dict entry.

    Returns:
        Dict mapping requirement IDs to entry dicts with keys: statement,
        verification, waived, waiver_reason.
    """
    requirements: dict[str, dict] = {}
    current_id: Optional[str] = None
    current_entry: Optional[dict] = None

    for line in lines:
        req_match = _REQ_INLINE_ENTRY_PATTERN.match(line)
        if req_match:
            if current_id is not None and current_entry is not None:
                requirements[current_id] = current_entry
            current_id = req_match.group(1)
            current_entry = {
                "statement": req_match.group(2).strip(),
                "verification": [],
                "waived": False,
                "waiver_reason": "",
            }
            continue

        if current_entry is None:
            continue

        stripped_line = line.strip()

        if stripped_line.lower().startswith("verification:"):
            methods_text = stripped_line.split(":", 1)[1].strip()
            methods = [m.strip() for m in methods_text.split(",") if m.strip()]
            current_entry["verification"].extend(methods)
            continue

        waiver_match = re.match(r'^\[WAIVED\]\s*(.*)', stripped_line)
        if waiver_match:
            current_entry["waived"] = True
            current_entry["waiver_reason"] = waiver_match.group(1).strip()
            continue

    if current_id is not None and current_entry is not None:
        requirements[current_id] = current_entry

    return requirements


def parse_intent(intent_file: str) -> IntentParseResult:
    """Parse a structured natural language intent file.

    Extracts disposition-tagged entries, requirement IDs,
    waivers, section content, and inline requirements from
    an optional [requirements] section. Detects requirement
    ID schemes automatically using regex pattern matching.

    Emits a warning to stderr when [WAIVED] appears on a line
    that also contains a requirement ID pattern — this indicates
    a requirement waiver in the wrong file (D-025).

    Args:
        intent_file: Path to .intent file.

    Returns:
        IntentParseResult with sections, req_ids, req_schemes,
        waivers, and inline_requirements.

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

        # Waiver detection: line contains [WAIVED]
        if "[WAIVED]" in stripped:
            # Warn when a req-ID-like pattern appears on the same [WAIVED] line —
            # requirement waivers belong in .req, not .intent (D-025).
            warn_ids = _WAIVER_REQ_WARN_PATTERN.findall(stripped)
            for req_id in warn_ids:
                print(
                    f"[pssgen] WARNING: Requirement waiver for {req_id} found in"
                    f" .intent — move to .req file (D-025)",
                    file=sys.stderr,
                )

            if current_section == "requirements":
                # Inline req waiver: keep in section content for post-processing.
                # Do not add to the intent-file waivers list.
                sections[current_section].append(stripped)
            else:
                # Standard intent-file waiver (coverage item waiver).
                waiver_ids = _extract_req_ids(stripped)
                waived_match = re.search(r'\[WAIVED\](.*)', stripped)
                item_text = waived_match.group(1).strip() if waived_match else stripped
                item_clean = _REQ_ID_PATTERN.sub("", item_text).strip()
                waivers.append({
                    "item": item_clean,
                    "reason": item_clean,
                    "req_ids": waiver_ids,
                })
            continue

        # Non-waiver content line: add to current section
        if current_section is not None:
            sections[current_section].append(stripped)

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

    # Parse inline requirements from the [requirements] section if present
    inline_requirements: dict[str, dict] = {}
    if "requirements" in sections:
        inline_requirements = _parse_inline_requirements(sections["requirements"])

    return IntentParseResult(
        sections=sections,
        req_ids=unique_ids,
        req_schemes=unique_schemes,
        waivers=waivers,
        inline_requirements=inline_requirements,
    )
