# ===========================================================
# FILE:         ir.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Defines the append-only data model shared between parser, agents,
#   checkers, and emitters. New fields are Optional with None default.
#   Existing fields are never renamed, removed, or retyped.
#
# LAYER:        2 — IR
# PHASE:        v0
#
# FUNCTIONS:
#   Port  (dataclass)
#     Single top-level HDL port with name, direction, width, and role.
#   IR  (dataclass)
#     Vendor-neutral pipeline data model carrying all parser outputs and
#     phase-specific extensions.
#
# DEPENDENCIES:
#   Standard library:  dataclasses, typing
#   Internal:          none
#
# HISTORY:
#   v0    2026-03-27  SB  Initial Port and IR dataclasses
#   v1a   2026-03-27  SB  Added pss_intent Optional field
#   v2b   2026-03-27  SB  Added pss_model Optional field
#   v3a   2026-03-28  SB  Added requirement_ids, requirement_schemes, intent_waivers, intent_gaps
#
# ===========================================================
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
    # v3a+: requirement traceability fields (append-only)
    requirement_ids: list[str] = field(default_factory=list)
    requirement_schemes: list[str] = field(default_factory=list)
    intent_waivers: list[dict] = field(default_factory=list)
    intent_gaps: list[str] = field(default_factory=list)
