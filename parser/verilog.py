# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""parser/verilog.py — Verilog-to-IR parser.

Phase: v0
Layer: 1 (parser)

Extracts design name, parameters, and top-level port metadata from Verilog
source and converts the result into IR.
"""
import re
from ir import IR, Port


CLOCK_NAMES  = {"clk", "clock", "clk_i", "sys_clk"}
RESET_N_NAMES = {"rst_n", "reset_n", "aresetn", "nreset"}
RESET_NAMES  = {"rst", "reset", "rst_i"}


class ParseError(Exception):
    """Raised when a Verilog source file cannot be parsed into IR."""

    pass


def _classify_role(name: str, direction: str) -> str:
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


def parse(source_file: str, top_module: str | None) -> IR:
    """Parse a Verilog source file into IR.

    Args:
        source_file: Path to the Verilog file to parse.
        top_module: Optional top module override.

    Returns:
        IR populated with design name, parameters, and port metadata.

    Raises:
        ParseError: If module or port extraction fails.
    """
    with open(source_file) as f:
        src = f.read()

    # Extract module name
    mod_match = re.search(r'\bmodule\s+(\w+)', src)
    if not mod_match:
        raise ParseError(f"No module declaration found in {source_file}")
    design_name = top_module or mod_match.group(1)

    # Extract parameters
    params = {}
    for m in re.finditer(r'parameter\s+\w+\s+(\w+)\s*=\s*([^,\)]+)', src):
        params[m.group(1)] = m.group(2).strip()

    # Extract ports — handles: input/output logic [W:0] name
    ports = []
    port_pattern = re.compile(
        r'\b(input|output|inout)\s+(?:logic\s+)?(?:\[(\d+):(\d+)\]\s+)?(\w+)'
    )
    for m in port_pattern.finditer(src):
        direction = m.group(1)
        msb = int(m.group(2)) if m.group(2) else 0
        lsb = int(m.group(3)) if m.group(3) else 0
        width = msb - lsb + 1
        name = m.group(4)
        if name in {"logic", "wire", "reg", "signed", "unsigned"}:
            continue
        role = _classify_role(name, direction)
        ports.append(Port(name=name, direction=direction, width=width, role=role))

    if not ports:
        raise ParseError(f"No ports extracted from {source_file}")

    return IR(
        design_name=design_name,
        hdl_source=source_file,
        hdl_language="verilog",
        ports=ports,
        parameters=params,
        emission_target="vivado",
        output_dir="./out",
    )
