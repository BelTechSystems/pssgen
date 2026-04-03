# ===========================================================
# FILE:         parser/regmap_parser.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Reads register map data from either an .xlsx spreadsheet (the four-sheet
#   pssgen register map format) or a plain English .intent file containing a
#   "register map:" section. Returns a normalized register_map dict that is
#   stored in ir.register_map and consumed by downstream agents (v4+).
#
# LAYER:        1 — parser
# PHASE:        v4a
#
# FUNCTIONS:
#   parse_regmap(source_file)
#     Dispatch to _parse_xlsx or _parse_intent_regmap based on extension.
#     Returns normalized register_map dict.
#   _parse_xlsx(source_file)
#     Read Globals, Blocks, RegisterMap, and Enums sheets from an .xlsx file.
#   _parse_intent_regmap(content)
#     Extract a register map: section from plain English intent content.
#
# DEPENDENCIES:
#   Standard library:  re, os
#   Internal:          parser.dispatch (ParseError)
#
# HISTORY:
#   v4a   2026-04-03  SB  Initial implementation; xlsx + plain English register map parsing
#
# ===========================================================
"""parser/regmap_parser.py — Register map spreadsheet and intent section parser.

Phase: v4a
Layer: 1 (parser)

Parses register map data from a pssgen-format .xlsx spreadsheet or from a
``register map:`` section embedded in a .intent file. The returned dict has
four keys (globals, blocks, registers, enums) and is stored in ir.register_map.
"""
import re
import os

from parser.verilog import ParseError


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_regmap(source_file: str) -> dict:
    """Parse a register map from spreadsheet or intent.

    Dispatches to ``_parse_xlsx`` for ``.xlsx`` files or
    ``_parse_intent_regmap`` for ``.intent`` files.

    Args:
        source_file: Path to ``.xlsx`` or ``.intent`` file.

    Returns:
        register_map dict with keys: ``globals``, ``blocks``,
        ``registers``, ``enums``.

    Raises:
        ValueError: If the file extension is not ``.xlsx`` or ``.intent``.
        ParseError: If the file cannot be parsed.
    """
    ext = os.path.splitext(source_file)[1].lower()
    if ext == ".xlsx":
        return _parse_xlsx(source_file)
    elif ext == ".intent":
        with open(source_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        return _parse_intent_regmap(content)
    else:
        raise ValueError(
            f"register map file must be .xlsx or .intent, got '{ext}'"
        )


# ---------------------------------------------------------------------------
# XLSX parser
# ---------------------------------------------------------------------------

def _parse_xlsx(source_file: str) -> dict:
    """Read a pssgen-format register map workbook.

    Requires the ``openpyxl`` package. Opens the workbook in read-only mode
    to minimise memory use on large spreadsheets.

    Args:
        source_file: Path to the ``.xlsx`` workbook.

    Returns:
        Normalised register_map dict.

    Raises:
        ParseError: If required sheets are missing or openpyxl is unavailable.
    """
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise ParseError(
            "openpyxl is required for register map parsing. "
            "Install it with: pip install openpyxl"
        ) from exc

    try:
        wb = load_workbook(source_file, read_only=True, data_only=True)
    except Exception as exc:
        raise ParseError(f"Cannot open register map workbook: {exc}") from exc

    globals_dict = _read_globals_sheet(wb)
    blocks_list = _read_blocks_sheet(wb)
    registers_list = _read_registermap_sheet(wb)
    enums_dict = _read_enums_sheet(wb)

    wb.close()

    return {
        "globals": globals_dict,
        "blocks": blocks_list,
        "registers": registers_list,
        "enums": enums_dict,
    }


def _is_example_row(value: str | None) -> bool:
    """Return True if the cell value marks a template example row."""
    if value is None:
        return False
    return str(value).startswith("[EXAMPLE")


def _str_or_none(value) -> str | None:
    """Convert a cell value to a stripped string, or None if blank."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _read_globals_sheet(wb) -> dict:
    """Extract the Globals sheet into a flat key→value dict."""
    if "Globals" not in wb.sheetnames:
        return {}

    ws = wb["Globals"]
    result: dict = {}
    # Skip row 1 (cover note or header). Read from row 2 onwards.
    # For workbooks without the cover note, row 2 is still the header — we
    # detect the header by checking whether the first cell says "Key".
    # Strategy: read all rows, skip rows where key is None or "Key" (header)
    # or starts with "pssgen Register" (cover note), or starts with "[EXAMPLE".
    for row in ws.iter_rows(min_row=2, values_only=True):
        key = _str_or_none(row[0] if len(row) > 0 else None)
        if key is None:
            continue
        if key.lower() == "key":
            continue
        if key.startswith("pssgen Register"):
            continue
        if _is_example_row(key):
            continue
        value = _str_or_none(row[1] if len(row) > 1 else None)
        result[key] = value if value is not None else ""
    return result


def _read_blocks_sheet(wb) -> list:
    """Extract the Blocks sheet into a list of block dicts."""
    if "Blocks" not in wb.sheetnames:
        return []

    ws = wb["Blocks"]
    result = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        block_name = _str_or_none(row[0] if len(row) > 0 else None)
        if block_name is None:
            continue
        if block_name.lower() == "block_name":
            continue  # stray header row
        if _is_example_row(block_name):
            continue
        result.append({
            "block_name":      block_name,
            "base_address":    _str_or_none(row[1] if len(row) > 1 else None) or "",
            "data_width_bits": _str_or_none(row[2] if len(row) > 2 else None) or "32",
            "reset_domain":    _str_or_none(row[3] if len(row) > 3 else None) or "",
            "clock_domain":    _str_or_none(row[4] if len(row) > 4 else None) or "",
            "description":     _str_or_none(row[5] if len(row) > 5 else None) or "",
        })
    return result


def _read_registermap_sheet(wb) -> list:
    """Group RegisterMap rows by (block, reg, offset) and return register list."""
    if "RegisterMap" not in wb.sheetnames:
        return []

    ws = wb["RegisterMap"]
    # Collect all valid field rows first
    raw_rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if len(row) < 6:
            continue
        block_name = _str_or_none(row[0])
        field_name = _str_or_none(row[5])
        if block_name is None or field_name is None:
            continue
        if block_name.lower() == "block_name":
            continue
        if _is_example_row(block_name):
            continue
        raw_rows.append(row)

    # Group into registers preserving insertion order
    reg_map: dict[tuple, dict] = {}
    reg_order: list[tuple] = []

    for row in raw_rows:
        block   = _str_or_none(row[0]) or ""
        reg_name = _str_or_none(row[1]) or ""
        reg_desc = _str_or_none(row[2]) or ""
        offset  = _str_or_none(row[3]) or ""
        width   = row[4]

        key = (block, reg_name, offset)
        if key not in reg_map:
            try:
                reg_width = int(width) if width is not None else 32
            except (ValueError, TypeError):
                reg_width = 32
            reg_map[key] = {
                "block":       block,
                "name":        reg_name,
                "description": reg_desc,
                "offset":      offset,
                "width":       reg_width,
                "fields":      [],
            }
            reg_order.append(key)

        field = _parse_field_row(row)
        reg_map[key]["fields"].append(field)

    return [reg_map[k] for k in reg_order]


def _parse_field_row(row) -> dict:
    """Extract and normalise a single field row from the RegisterMap sheet."""
    def _int_val(v, default=0):
        try:
            return int(v) if v is not None else default
        except (ValueError, TypeError):
            return default

    def _bool_yes(v):
        return str(v).strip().upper() == "YES" if v is not None else False

    return {
        "field_name":        _str_or_none(row[5]) or "",
        "bit_offset":        _int_val(row[6]),
        "bit_width":         _int_val(row[7], default=1),
        "access":            _str_or_none(row[8]) or "NA",
        "reset_value":       _str_or_none(row[9]) or "0x0",
        "volatile":          _bool_yes(row[10]),
        "hw_access":         _str_or_none(row[11]) or "NA",
        "sw_access":         _str_or_none(row[12]) or "NA",
        "field_kind":        _str_or_none(row[13]) or "normal",
        "enum_ref":          _str_or_none(row[14]),
        "uvm_has_coverage":  _bool_yes(row[15]),
        "req_id":            _str_or_none(row[16]),
        "pss_action":        _str_or_none(row[17]),
        "hdl_path":          _str_or_none(row[18]),
        "description":       _str_or_none(row[19]) or "",
    }


def _read_enums_sheet(wb) -> dict:
    """Group Enums sheet rows by enum_name and return a name→values dict."""
    if "Enums" not in wb.sheetnames:
        return {}

    ws = wb["Enums"]
    result: dict = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        enum_name = _str_or_none(row[0] if len(row) > 0 else None)
        if enum_name is None:
            continue
        if enum_name.lower() == "enum_name":
            continue
        if _is_example_row(enum_name):
            continue
        try:
            value = int(row[1]) if row[1] is not None else 0
        except (ValueError, TypeError):
            value = 0
        symbol      = _str_or_none(row[2] if len(row) > 2 else None) or ""
        description = _str_or_none(row[3] if len(row) > 3 else None) or ""
        if enum_name not in result:
            result[enum_name] = []
        result[enum_name].append({
            "value":       value,
            "symbol":      symbol,
            "description": description,
        })

    return result


# ---------------------------------------------------------------------------
# Plain English register map parser
# ---------------------------------------------------------------------------

# Patterns for plain English format
_REG_HEADING = re.compile(
    r"^\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+register\s+at\s+offset\s+"
    r"(?P<offset>0x[0-9A-Fa-f_]+)"
    r"(?P<flags>[^:]*):",
    re.IGNORECASE,
)
_FIELD_LINE = re.compile(
    r"^\s+(?P<fname>[A-Za-z_][A-Za-z0-9_]*)\s+field\s+\[(?P<msb>\d+):(?P<lsb>\d+)\]\s+"
    r"(?P<access>[A-Z0-9]+)"
    r"(?:\s+reset=(?P<reset>\S+))?"
    r"(?:\s+[—\-]+\s+(?P<desc>.*))?",
    re.IGNORECASE,
)
_SECTION_HEADING = re.compile(r"^[A-Za-z].*:\s*$")


def _parse_intent_regmap(content: str) -> dict:
    """Parse a ``register map:`` section from plain English intent content.

    Handles ``.intent`` file content that contains a ``register map:``
    section with register and field descriptions. This is Tier 2 — metadata
    is limited and no enum definitions are produced.

    The function finds the ``register map:`` section, stops at the next
    top-level section heading (a line ending in ``:`` with no leading
    whitespace), and parses registers and fields from the section body.

    Args:
        content: Full text of the intent file or a partial string containing
                 a ``register map:`` section.

    Returns:
        Normalised register_map dict with minimal globals, one DEFAULT block,
        parsed registers, and empty enums.
    """
    lines = content.splitlines()

    # Find the register map: section
    in_regmap = False
    regmap_lines: list[str] = []

    for line in lines:
        stripped = line.rstrip()
        # Detect section start (top-level, no leading whitespace, ends with :)
        if _SECTION_HEADING.match(stripped):
            heading_lower = stripped.lower().rstrip(":")
            if heading_lower.strip() == "register map":
                in_regmap = True
                continue
            elif in_regmap:
                # A new top-level section — stop collecting
                break
        if in_regmap:
            regmap_lines.append(stripped)

    registers: list[dict] = []
    current_reg: dict | None = None

    for line in regmap_lines:
        if not line.strip():
            continue

        reg_match = _REG_HEADING.match(line)
        if reg_match:
            current_reg = {
                "block":       "DEFAULT",
                "name":        reg_match.group("name").upper(),
                "description": f"{reg_match.group('name')} register",
                "offset":      reg_match.group("offset"),
                "width":       32,
                "fields":      [],
            }
            # Mark all fields volatile if "(volatile)" in flags
            flags = reg_match.group("flags") or ""
            current_reg["_volatile_default"] = "volatile" in flags.lower()
            registers.append(current_reg)
            continue

        field_match = _FIELD_LINE.match(line)
        if field_match and current_reg is not None:
            msb = int(field_match.group("msb"))
            lsb = int(field_match.group("lsb"))
            bit_offset = lsb
            bit_width  = msb - lsb + 1
            access = field_match.group("access").upper()
            reset_val = field_match.group("reset") or "0x0"
            description = (field_match.group("desc") or "").strip()
            is_volatile = current_reg.get("_volatile_default", False)

            current_reg["fields"].append({
                "field_name":       field_match.group("fname").upper(),
                "bit_offset":       bit_offset,
                "bit_width":        bit_width,
                "access":           access,
                "reset_value":      reset_val,
                "volatile":         is_volatile,
                "hw_access":        "NA",
                "sw_access":        access,
                "field_kind":       "normal",
                "enum_ref":         None,
                "uvm_has_coverage": True,
                "req_id":           None,
                "pss_action":       None,
                "hdl_path":         None,
                "description":      description,
            })

    # Strip internal parsing scratch key
    for reg in registers:
        reg.pop("_volatile_default", None)

    # Derive block list from parsed registers
    blocks = [{"block_name": "DEFAULT", "base_address": "0x0",
               "data_width_bits": "32", "reset_domain": "",
               "clock_domain": "", "description": ""}] if registers else []

    return {
        "globals": {},
        "blocks":  blocks,
        "registers": registers,
        "enums": {},
    }
