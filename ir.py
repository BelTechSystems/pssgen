"""
IR: vendor-neutral intermediate representation.
APPEND-ONLY: never rename or remove fields. New fields are Optional with None default.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    name: str
    direction: str   # "input" | "output" | "inout"
    width: int
    role: str        # "clock" | "reset_n" | "reset" | "control" | "data"


@dataclass
class IR:
    design_name: str
    hdl_source: str
    hdl_language: str          # "verilog" | "systemverilog" | "vhdl"
    ports: list[Port]
    parameters: dict
    emission_target: str       # "vivado" | "questa" | "generic"
    output_dir: str
    # v1+: append new Optional fields below this line
    pss_intent: Optional[str] = None
