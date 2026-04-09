# ===========================================================
# FILE:         parser/systemverilog.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Parses a constrained subset of SystemVerilog module declarations into IR.
#   Supports logic scalar and logic [N:0] vector port types with integer
#   parameters as symbolic bounds. Port directions input, output, and inout
#   are supported. Only the module header (parameters + port list) is read;
#   always_ff bodies, localparams, and assign statements are ignored.
#
# LAYER:        1 — parser
# PHASE:        v5a
#
# FUNCTIONS:
#   parse(source_file, top_module)
#     Parse a SystemVerilog source file and return a populated IR instance.
#
# DEPENDENCIES:
#   Standard library:  re
#   Internal:          ir
#
# HISTORY:
#   v0    2026-03-27  SB  Stub placeholder; import path registered for v1
#   v5a   2026-04-08  SB  Working implementation; logic scalar/vector ports,
#                          parameter bounds, inline comment stripping
#
# ===========================================================
"""parser/systemverilog.py — Minimal SystemVerilog module parser.

Phase: v5a
Layer: 1 (parser)

Parses a constrained subset of SystemVerilog module declarations into IR,
including integer parameters and logic/logic[N:0] ports.
"""

from __future__ import annotations

import re

from ir import IR, Port


CLOCK_NAMES = {"clk", "clock", "clk_i", "sys_clk", "axi_aclk"}
RESET_N_NAMES = {"rst_n", "reset_n", "aresetn", "axi_aresetn", "nreset"}
RESET_NAMES = {"rst", "reset", "rst_i"}


class ParseError(Exception):
    """Raised when SV text cannot be converted into IR."""
    pass


def _classify_role(name: str, direction: str) -> str:
    """Classify a port semantic role from name and direction.

    Args:
        name: Port name.
        direction: IR direction value.

    Returns:
        Role string used by downstream generation.
    """
    n = name.lower()
    if n in CLOCK_NAMES:
        return "clock"
    if n in RESET_N_NAMES:
        return "reset_n"
    if n in RESET_NAMES:
        return "reset"
    if direction == "output":
        return "data"
    return "control"


def _eval_int_token(token: str, parameters: dict[str, str]) -> int:
    """Resolve an integer token from literal, expression, or parameter reference.

    Handles simple expressions of the form ``PARAM-1`` (parameter minus
    literal) which appear in SV port declarations like ``[WIDTH-1:0]``.

    Args:
        token: Numeric literal or parameter expression.
        parameters: Parsed parameter defaults.

    Returns:
        Integer value for width computation.

    Raises:
        ParseError: If the token cannot be resolved.
    """
    t = token.strip()

    # Plain integer literal
    if re.fullmatch(r"\d+", t):
        return int(t)

    # Simple "PARAM - literal" or "PARAM + literal" expression
    m = re.fullmatch(r"([A-Za-z_]\w*)\s*([-+])\s*(\d+)", t)
    if m:
        param_name, op, literal = m.group(1), m.group(2), m.group(3)
        base_str = parameters.get(param_name, "").strip()
        if re.fullmatch(r"\d+", base_str):
            base = int(base_str)
            return base - int(literal) if op == "-" else base + int(literal)

    # Plain parameter reference
    if t in parameters:
        val = parameters[t].strip()
        if re.fullmatch(r"\d+", val):
            return int(val)

    raise ParseError(f"Unsupported vector bound token '{token}'")


def _width_from_decl(range_str: str | None, port_name: str,
                     parameters: dict[str, str]) -> int:
    """Compute port width from an optional bracket range string.

    Args:
        range_str: Text inside ``[...]``, e.g. ``"31:0"`` or ``"WIDTH-1:0"``,
            or None for scalar ports.
        port_name: Port name for error reporting.
        parameters: Parsed parameter defaults.

    Returns:
        Bit width as an integer (1 for scalars).

    Raises:
        ParseError: If the range cannot be resolved.
    """
    if range_str is None:
        return 1

    m = re.fullmatch(
        r"\s*([A-Za-z_]\w*(?:\s*[-+]\s*\d+)?|\d+)\s*:\s*"
        r"([A-Za-z_]\w*(?:\s*[-+]\s*\d+)?|\d+)\s*",
        range_str,
    )
    if not m:
        raise ParseError(
            f"Unsupported port range '[{range_str}]' for port '{port_name}'"
        )
    msb = _eval_int_token(m.group(1), parameters)
    lsb = _eval_int_token(m.group(2), parameters)
    return abs(msb - lsb) + 1


def _normalize_direction(mode: str) -> str:
    """Map SV port direction text to IR direction values.

    Args:
        mode: SV direction text.

    Returns:
        IR direction value.
    """
    m = mode.lower().strip()
    if m == "input":
        return "input"
    if m == "output":
        return "output"
    return "inout"


def _strip_comments(text: str) -> str:
    """Remove // line comments and /* */ block comments from text.

    Args:
        text: Source text possibly containing SV comments.

    Returns:
        Text with all comments replaced by a single space.
    """
    # Block comments first
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    # Line comments
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def _parse_parameters(src: str) -> dict[str, str]:
    """Extract parameter defaults from a SV module header.

    Looks for the ``#(...)`` parameter block that precedes the port list.

    Args:
        src: Comment-stripped source text.

    Returns:
        Dict mapping parameter name → default value string.
    """
    params: dict[str, str] = {}

    # Match #( ... ) — the parameter block; stop at the matching )
    # then require ( immediately after (start of port list)
    m = re.search(r"#\s*\((.*?)\)\s*\(", src, re.DOTALL)
    if not m:
        return params

    block = m.group(1)

    # Each declaration: [parameter [type]] NAME = VALUE
    for decl in re.split(r",", block):
        decl = decl.strip()
        if not decl:
            continue
        # Strip optional 'parameter [type]' prefix
        decl_body = re.sub(
            r"^\s*parameter\s+(?:int|integer|logic|bit|byte|shortint|"
            r"longint|string)?\s*",
            "",
            decl,
            flags=re.IGNORECASE,
        ).strip()
        pm = re.match(r"([A-Za-z_]\w*)\s*=\s*(.+)", decl_body)
        if pm:
            name = pm.group(1).strip()
            val = pm.group(2).strip().rstrip(",").strip()
            # Remove underscores from numeric literals for integer comparison
            clean_val = val.replace("_", "")
            params[name] = clean_val if re.fullmatch(r"\d+", clean_val) else val

    return params


def _extract_port_block(src: str) -> str:
    """Extract the port list text from a SV module declaration.

    Finds the opening ``(`` of the port list (after the optional ``#(...)``
    parameter block) and returns everything up to the matching ``)``.

    Args:
        src: Comment-stripped source text.

    Returns:
        Content of the outer port-list parentheses.

    Raises:
        ParseError: If no port list can be found.
    """
    mod_m = re.search(r"\bmodule\s+\w+", src)
    if not mod_m:
        raise ParseError("No module declaration found")

    search_start = mod_m.end()

    # Skip optional #(...) parameter block
    param_m = re.search(r"#\s*\(", src[search_start:])
    if param_m:
        start = search_start + param_m.end()
        depth = 1
        i = start
        while i < len(src) and depth:
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
            i += 1
        search_start = i

    # Find the port-list opening paren
    port_open = src.find("(", search_start)
    if port_open < 0:
        raise ParseError("No port list found in module declaration")

    depth = 1
    i = port_open + 1
    while i < len(src) and depth:
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
        i += 1

    return src[port_open + 1 : i - 1]


def parse(source_file: str, top_module: str | None) -> IR:
    """Parse a constrained SystemVerilog module declaration into IR.

    Reads only the module header: parameter list and port declarations.
    The module body (always blocks, assigns, localparams) is ignored.

    Args:
        source_file: Path to the .sv source file.
        top_module: Optional top module name override.

    Returns:
        Populated IR instance with ``hdl_language="systemverilog"``.

    Raises:
        ParseError: If required module/port data cannot be parsed.
    """
    with open(source_file, encoding="utf-8") as f:
        raw_src = f.read()

    # Find module name before stripping (preserves original identifiers)
    mod_m = re.search(r"\bmodule\s+(\w+)", raw_src)
    if not mod_m:
        raise ParseError(f"No module declaration found in {source_file}")
    design_name = top_module or mod_m.group(1)

    # Strip comments for structural parsing
    src = _strip_comments(raw_src)

    parameters = _parse_parameters(src)

    port_block = _extract_port_block(src)

    # Split on commas at parenthesis depth 0
    port_decls: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in port_block:
        if ch in "([":
            depth += 1
            current.append(ch)
        elif ch in ")]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            port_decls.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        port_decls.append("".join(current).strip())

    ports: list[Port] = []

    # Port declaration pattern:
    #   <direction> [logic|wire|reg] [signed|unsigned] [[range]] <name>
    port_pat = re.compile(
        r"^\s*(input|output|inout)\s+"
        r"(?:logic|wire|reg)?\s*"
        r"(?:signed|unsigned)?\s*"
        r"(?:\[([^\]]+)\])?\s*"
        r"([A-Za-z_]\w*)\s*$",
        re.IGNORECASE,
    )

    for decl in port_decls:
        decl = " ".join(decl.split())
        if not decl:
            continue
        m = port_pat.match(decl)
        if not m:
            continue

        direction = _normalize_direction(m.group(1))
        range_str = m.group(2)  # None for scalars
        name = m.group(3)

        width = _width_from_decl(range_str, name, parameters)
        role = _classify_role(name, direction)
        ports.append(Port(name=name, direction=direction, width=width, role=role))

    if not ports:
        raise ParseError(f"No ports extracted from {source_file}")

    return IR(
        design_name=design_name,
        hdl_source=source_file,
        hdl_language="systemverilog",
        ports=ports,
        parameters=parameters,
        emission_target="vivado",
        output_dir="./out",
    )
