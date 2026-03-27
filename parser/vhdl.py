# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""parser/vhdl.py — Minimal VHDL entity parser.

Phase: v1a
Layer: 1 (parser)

Parses a constrained subset of VHDL entity declarations into IR, including
integer generics and std_logic/std_logic_vector ports.
"""

from __future__ import annotations

import re

from ir import IR, Port


CLOCK_NAMES = {"clk", "clock", "clk_i", "sys_clk"}
RESET_N_NAMES = {"rst_n", "reset_n", "aresetn", "nreset"}
RESET_NAMES = {"rst", "reset", "rst_i"}


class ParseError(Exception):
    """Raised when VHDL text cannot be converted into IR."""

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
    """Resolve an integer token from literal or generic reference.

    Args:
        token: Numeric literal text or generic name.
        parameters: Parsed generic defaults.

    Returns:
        Integer value for width computation.

    Raises:
        ParseError: If the token cannot be resolved.
    """
    t = token.strip()
    if re.fullmatch(r"\d+", t):
        return int(t)
    if t in parameters and re.fullmatch(r"\d+", parameters[t].strip()):
        return int(parameters[t].strip())
    raise ParseError(f"Unsupported vector bound token '{token}'")


def _width_from_type(port_type: str, port_name: str, parameters: dict[str, str]) -> int:
    """Compute a port width from a constrained VHDL type string.

    Args:
        port_type: VHDL type expression from the port declaration.
        port_name: Port name for error reporting.
        parameters: Generic defaults for resolving symbolic bounds.

    Returns:
        Bit width as an integer.

    Raises:
        ParseError: If the type is unsupported.
    """
    ptype = " ".join(port_type.strip().split())
    if ptype.lower() == "std_logic":
        return 1

    downto_match = re.fullmatch(
        r"std_logic_vector\(\s*([A-Za-z_]\w*|\d+)\s+downto\s+([A-Za-z_]\w*|\d+)\s*\)",
        ptype,
        flags=re.IGNORECASE,
    )
    if downto_match:
        msb = _eval_int_token(downto_match.group(1), parameters)
        lsb = _eval_int_token(downto_match.group(2), parameters)
        return abs(msb - lsb) + 1

    to_match = re.fullmatch(
        r"std_logic_vector\(\s*([A-Za-z_]\w*|\d+)\s+to\s+([A-Za-z_]\w*|\d+)\s*\)",
        ptype,
        flags=re.IGNORECASE,
    )
    if to_match:
        lsb = _eval_int_token(to_match.group(1), parameters)
        msb = _eval_int_token(to_match.group(2), parameters)
        return abs(msb - lsb) + 1

    raise ParseError(f"Unsupported VHDL port type '{ptype}' for port '{port_name}'")


def _normalize_direction(mode: str) -> str:
    """Map VHDL port mode text to IR direction values.

    Args:
        mode: VHDL mode text.

    Returns:
        IR direction value.
    """
    m = mode.lower()
    if m == "in":
        return "input"
    if m in {"out", "buffer"}:
        return "output"
    return "inout"


def _parse_generics(src: str) -> dict[str, str]:
    """Extract integer generic defaults from a VHDL entity block.

    Args:
        src: Full VHDL source text.

    Returns:
        Generic name/value map as strings.
    """
    generics: dict[str, str] = {}
    generic_match = re.search(r"\bgeneric\s*\((.*?)\)\s*;", src, re.IGNORECASE | re.DOTALL)
    if not generic_match:
        return generics

    block = generic_match.group(1)
    for declaration in block.split(";"):
        decl = " ".join(declaration.strip().split())
        if not decl:
            continue
        m = re.fullmatch(
            r"([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*:\s*integer\s*:=\s*([^;]+)",
            decl,
            flags=re.IGNORECASE,
        )
        if not m:
            continue
        names = [name.strip() for name in m.group(1).split(",")]
        default = m.group(2).strip()
        for name in names:
            generics[name] = default

    return generics


def parse(source_file: str, top_module: str | None) -> IR:
    """Parse constrained VHDL entity text into IR.

    Args:
        source_file: Path to the VHDL source file.
        top_module: Optional top entity override.

    Returns:
        Parsed IR instance with `hdl_language="vhdl"`.

    Raises:
        ParseError: If required entity/port data cannot be parsed.
    """
    with open(source_file) as f:
        src = f.read()

    entity_match = re.search(r"\bentity\s+(\w+)\s+is", src, re.IGNORECASE)
    if not entity_match:
        raise ParseError(f"No entity declaration found in {source_file}")
    design_name = top_module or entity_match.group(1)

    parameters = _parse_generics(src)

    port_match = re.search(r"\bport\s*\((.*?)\)\s*;", src, re.IGNORECASE | re.DOTALL)
    if not port_match:
        raise ParseError(f"No port declaration block found in {source_file}")

    ports: list[Port] = []
    port_block = port_match.group(1)
    for declaration in port_block.split(";"):
        decl = " ".join(declaration.strip().split())
        if not decl:
            continue
        decl_match = re.fullmatch(
            r"([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*:\s*(in|out|inout|buffer)\s+(.+)",
            decl,
            flags=re.IGNORECASE,
        )
        if not decl_match:
            continue

        names = [name.strip() for name in decl_match.group(1).split(",")]
        direction = _normalize_direction(decl_match.group(2))
        port_type = decl_match.group(3).strip()

        for name in names:
            width = _width_from_type(port_type, name, parameters)
            role = _classify_role(name, direction)
            ports.append(Port(name=name, direction=direction, width=width, role=role))

    if not ports:
        raise ParseError(f"No ports extracted from {source_file}")

    return IR(
        design_name=design_name,
        hdl_source=source_file,
        hdl_language="vhdl",
        ports=ports,
        parameters=parameters,
        emission_target="vivado",
        output_dir="./out",
    )
