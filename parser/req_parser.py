# Copyright (c) 2026 BelTech Systems LLC and contributors
# SPDX-License-Identifier: MIT
"""parser/req_parser.py — Requirements file (.req) parser.

Phase: v3a
Layer: 1 (parser)

Parses .req files containing structured requirement entries with optional
verification methods and waiver annotations. Each entry is keyed by its
requirement ID.
"""
import re
from dataclasses import dataclass, field


# Pattern to match requirement ID lines: [SYS-REQ-001] statement text.
# Segments after the first may start with a digit (e.g. -001 in SYS-REQ-001).
_REQ_LINE_PATTERN = re.compile(
    r'^\[([A-Z][A-Z0-9]*(?:-[A-Z0-9][A-Z0-9]*){1,4})\]\s*(.*)'
)
# Pattern to match waiver annotation lines: [WAIVED] reason
_WAIVER_LINE_PATTERN = re.compile(r'^\[WAIVED\]\s*(.*)')


@dataclass
class ReqParseResult:
    """Result of parsing a .req requirements file.

    Attributes:
        requirements: Mapping from requirement ID to requirement detail dict.
            Each dict has keys: "statement" (str), "verification" (list[str]),
            "waived" (bool), "waiver_reason" (str).
        waivers: List of waived requirement IDs.
    """
    requirements: dict[str, dict] = field(default_factory=dict)
    waivers: list[str] = field(default_factory=list)


def parse_req(req_file: str) -> ReqParseResult:
    """Parse a structured requirements file.

    Each requirement block starts with a [REQ-ID] line followed by optional
    ``verification:`` and ``[WAIVED]`` lines. Entries are terminated by the
    next [REQ-ID] line or end-of-file.

    Args:
        req_file: Path to the .req file to parse.

    Returns:
        ReqParseResult containing the requirements dict and waiver ID list.

    Raises:
        FileNotFoundError: If req_file does not exist.
        OSError: If the file cannot be read.
    """
    with open(req_file, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    requirements: dict[str, dict] = {}
    waivers: list[str] = []

    current_id: str | None = None
    current_entry: dict | None = None

    for raw_line in lines:
        line = raw_line.rstrip()

        # Skip comments and blank lines
        if not line or line.startswith("#"):
            continue

        # Check for a new requirement ID line
        req_match = _REQ_LINE_PATTERN.match(line)
        if req_match:
            # Flush previous entry before starting new one
            if current_id is not None and current_entry is not None:
                requirements[current_id] = current_entry
                if current_entry.get("waived"):
                    waivers.append(current_id)
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

        # Verification methods line
        if line.strip().lower().startswith("verification:"):
            methods_text = line.split(":", 1)[1].strip()
            methods = [m.strip() for m in methods_text.split(",") if m.strip()]
            current_entry["verification"].extend(methods)
            continue

        # Waiver annotation line
        waiver_match = _WAIVER_LINE_PATTERN.match(line.strip())
        if waiver_match:
            current_entry["waived"] = True
            current_entry["waiver_reason"] = waiver_match.group(1).strip()
            continue

    # Flush the last entry
    if current_id is not None and current_entry is not None:
        requirements[current_id] = current_entry
        if current_entry.get("waived"):
            waivers.append(current_id)

    return ReqParseResult(requirements=requirements, waivers=waivers)
