# ===========================================================
# FILE:         agents/ral_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   UVM RAL (Register Abstraction Layer) generation agent. Renders three
#   Jinja2 templates from ir.register_map to produce a uvm_reg_block class,
#   a packaging wrapper, and PSS-action-aligned register sequences. Generation
#   is always template-only — no LLM call is made (see D-018).
#
# LAYER:        3 — agents
# PHASE:        v4b
#
# FUNCTIONS:
#   generate_ral(ir, no_llm)
#     Render three RAL Jinja2 templates from ir.register_map.
#     Returns list of Artifacts or empty list if ir.register_map is None.
#   _build_ral_context(ir)
#     Build Jinja2 template context dict from ir.register_map.
#
# DEPENDENCIES:
#   Standard library:  os
#   External:          jinja2
#   Internal:          ir, agents.structure_gen
#
# HISTORY:
#   v4b   2026-04-03  SB  Initial implementation; reg_block, reg_pkg, reg_seq templates
#
# ===========================================================
"""agents/ral_gen.py — UVM RAL model generation agent.

Phase: v4b
Layer: 3 (agents)

Generates UVM RAL SystemVerilog from ir.register_map using three Jinja2
templates. Always template-only — no LLM call regardless of no_llm flag.
See DECISIONS.md D-018 for rationale.
"""

import os

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ir import IR
from agents.structure_gen import Artifact


TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "templates", "ral"
)

_TEMPLATES = [
    ("reg_block.sv.jinja", "{design_name}_reg_block.sv"),
    ("reg_pkg.sv.jinja",   "{design_name}_reg_pkg.sv"),
    ("reg_seq.sv.jinja",   "{design_name}_reg_seq.sv"),
]


def generate_ral(
    ir: IR,
    no_llm: bool = False,
) -> list[Artifact]:
    """Generate UVM RAL artifacts from register map.

    Renders three Jinja2 templates using ir.register_map data. Returns list
    of Artifact objects for the checker and emitter pipeline. Generation is
    always template-only regardless of ``no_llm`` (see D-018).

    Args:
        ir: Populated design IR with register_map set.
        no_llm: Accepted for interface consistency; has no effect — RAL
                generation is always template-only.

    Returns:
        List of three Artifacts:
          ``<design_name>_reg_block.sv``
          ``<design_name>_reg_pkg.sv``
          ``<design_name>_reg_seq.sv``
        Empty list if ``ir.register_map`` is None.
    """
    if ir.register_map is None:
        return []

    context = _build_ral_context(ir)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    artifacts: list[Artifact] = []
    for template_name, filename_pattern in _TEMPLATES:
        template = env.get_template(template_name)
        content = template.render(**context)
        filename = filename_pattern.format(design_name=ir.design_name)
        artifacts.append(Artifact(filename=filename, content=content))

    return artifacts


def _build_ral_context(ir: IR) -> dict:
    """Build Jinja2 template context from ir.register_map.

    Normalises globals values into the scalar entries the templates expect.
    Ensures each register's ``fields`` list is present.  Converts endianness
    string to UVM-style uppercase ("Little" → "LITTLE", "Big" → "BIG").

    Args:
        ir: Populated design IR with register_map set.

    Returns:
        Context dict with keys: design_name, registers, base_address,
        data_width_bytes, endianness, enums.
    """
    regmap = ir.register_map  # already verified non-None by caller
    globals_dict = regmap.get("globals", {})

    # Derive scalar values from globals with safe defaults
    base_address = globals_dict.get("base_address", "0x0") or "0x0"
    data_width_bits = globals_dict.get("data_width_bits", "32") or "32"
    try:
        data_width_bytes = int(str(data_width_bits)) // 8
    except (ValueError, TypeError):
        data_width_bytes = 4  # 32-bit default

    endianness_raw = globals_dict.get("endianness", "Little") or "Little"
    endianness = endianness_raw.strip().upper()  # "LITTLE" | "BIG"

    # Ensure registers list is safe — filter any entry without a fields list
    registers = [
        r for r in regmap.get("registers", [])
        if r.get("fields") is not None
    ]

    # Normalise field names: templates use field.name (not field.field_name)
    # Add a "name" alias so templates can use {{ field.name }}
    for reg in registers:
        for field in reg.get("fields", []):
            if "name" not in field:
                field["name"] = field.get("field_name", "")

    return {
        "design_name":      ir.design_name,
        "registers":        registers,
        "base_address":     base_address,
        "data_width_bytes": data_width_bytes,
        "endianness":       endianness,
        "enums":            regmap.get("enums", {}),
    }
