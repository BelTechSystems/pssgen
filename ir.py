# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""ir.py — Vendor-neutral intermediate representation.

Phase: v0
Layer: 2 (IR)

Defines append-only data contracts shared between parser, agents, checkers, and
emitters.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    """Single top-level HDL port description.

    Attributes:
        name: Port identifier.
        direction: Port direction ("input", "output", or "inout").
        width: Bit width of the port.
        role: Semantic role classification for generation and checking.
    """
    name: str
    direction: str   # "input" | "output" | "inout"
    width: int
    role: str        # "clock" | "reset_n" | "reset" | "control" | "data"


@dataclass
class IR:
    """Parsed design representation used by downstream layers.

    Attributes:
        design_name: Top-level design/module name.
        hdl_source: Source file path.
        hdl_language: HDL language identifier.
        ports: Extracted top-level port list.
        parameters: Module parameter name/value map.
        emission_target: Simulator/output target name.
        output_dir: Output directory for emitted artifacts.
        pss_intent: Optional PSS intent text (introduced in later phases).
        pss_model: Optional generated PSS source model text.
    """
    design_name: str
    hdl_source: str
    hdl_language: str          # "verilog" | "systemverilog" | "vhdl"
    ports: list[Port]
    parameters: dict
    emission_target: str       # "vivado" | "questa" | "generic"
    output_dir: str
    # v1+: append new Optional fields below this line
    pss_intent: Optional[str] = None
    pss_model: Optional[str] = None
