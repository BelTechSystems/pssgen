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
#   a packaging wrapper, and PSS-action-aligned register sequences. When the
#   register map contains two or more distinct blocks a system assembly
#   reg_map.sv is also rendered. Generation is always template-only (D-018).
#
# LAYER:        3 — agents
# PHASE:        v4c
#
# FUNCTIONS:
#   generate_ral(ir, no_llm)
#     Render three RAL Jinja2 templates from ir.register_map.
#     Appends system reg_map.sv artifact when 2+ blocks present.
#     Returns list of Artifacts or empty list if ir.register_map is None.
#   _build_ral_context(ir)
#     Build Jinja2 template context dict from ir.register_map (single-block path).
#   _build_block_context(ir, block_name, block_regs)
#     Build per-block context for multi-block path; design_name = block_name.lower().
#   _build_system_context(ir)
#     Build system reg_map.sv context when 2+ distinct blocks present.
#
# DEPENDENCIES:
#   Standard library:  os
#   External:          jinja2
#   Internal:          ir, agents.structure_gen
#
# HISTORY:
#   v4b   2026-04-03  SB  Initial implementation; reg_block, reg_pkg, reg_seq templates
#   v4c   2026-04-05  SB  System assembly: reg_map.sv when 2+ blocks present
#
# ===========================================================
"""agents/ral_gen.py — UVM RAL model generation agent.

Phase: v4c
Layer: 3 (agents)

Generates UVM RAL SystemVerilog from ir.register_map using three Jinja2
templates. When the register map contains two or more distinct block names,
a system-level reg_map.sv is also produced. Always template-only — no LLM
call regardless of no_llm flag (see DECISIONS.md D-018).
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

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    # Collect distinct block names in register order
    all_regs = ir.register_map.get("registers", [])
    seen_blocks: list[str] = []
    for reg in all_regs:
        bn = reg.get("block", "")
        if bn and bn not in seen_blocks:
            seen_blocks.append(bn)

    artifacts: list[Artifact] = []

    if len(seen_blocks) <= 1:
        # Single-block (or no-block) path.
        # Use block_name as prefix when a block is identified in the register map
        # so the output file is named {block}_reg_block.sv.  Fall back to
        # ir.design_name only when the register map has no block data.
        if seen_blocks:
            block_name = seen_blocks[0]
            block_regs = [r for r in all_regs if r.get("block") == block_name]
            context = _build_block_context(ir, block_name, block_regs)
            prefix = block_name.lower()
        else:
            context = _build_ral_context(ir)
            prefix = ir.design_name
        for template_name, filename_pattern in _TEMPLATES:
            template = env.get_template(template_name)
            content = template.render(**context)
            filename = filename_pattern.format(design_name=prefix)
            artifacts.append(Artifact(filename=filename, content=content))
    else:
        # Multi-block path: generate one set of three RAL files per block,
        # using block_name (lowercased) as the design_name prefix.
        for block_name in seen_blocks:
            block_regs = [r for r in all_regs if r.get("block") == block_name]
            block_prefix = block_name.lower()
            block_ctx = _build_block_context(ir, block_name, block_regs)
            for template_name, filename_pattern in _TEMPLATES:
                template = env.get_template(template_name)
                content = template.render(**block_ctx)
                filename = filename_pattern.format(design_name=block_prefix)
                artifacts.append(Artifact(filename=filename, content=content))

        # System assembly artifact
        sys_ctx = _build_system_context(ir)
        if sys_ctx is not None:
            template = env.get_template("reg_map.sv.jinja")
            content = template.render(**sys_ctx)
            project_name = sys_ctx["project_name"]
            artifacts.append(Artifact(
                filename=f"{project_name}_reg_map.sv",
                content=content,
            ))

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


def _build_block_context(ir: IR, block_name: str, block_regs: list) -> dict:
    """Build Jinja2 context for a single block in a multi-block register map.

    Identical to :func:`_build_ral_context` except that ``design_name`` is set
    to the lowercased ``block_name`` and only the registers belonging to that
    block are included.

    Args:
        ir: Populated design IR.
        block_name: Block identifier (e.g. "GPIO", "COUNTER").
        block_regs: Pre-filtered list of register dicts for this block.

    Returns:
        Context dict matching the shape expected by the RAL templates.
    """
    regmap = ir.register_map or {}
    globals_dict = regmap.get("globals", {})

    # Look up this block's base_address from the blocks list
    blocks_list = regmap.get("blocks", [])
    base_address = "0x0"
    for blk in blocks_list:
        if blk.get("block_name", "").upper() == block_name.upper():
            base_address = blk.get("base_address", "0x0") or "0x0"
            break

    data_width_bits = globals_dict.get("data_width_bits", "32") or "32"
    try:
        data_width_bytes = int(str(data_width_bits)) // 8
    except (ValueError, TypeError):
        data_width_bytes = 4

    endianness_raw = globals_dict.get("endianness", "Little") or "Little"
    endianness = endianness_raw.strip().upper()

    registers = [r for r in block_regs if r.get("fields") is not None]
    for reg in registers:
        for field in reg.get("fields", []):
            if "name" not in field:
                field["name"] = field.get("field_name", "")

    return {
        "design_name":      block_name.lower(),
        "registers":        registers,
        "base_address":     base_address,
        "data_width_bytes": data_width_bytes,
        "endianness":       endianness,
        "enums":            regmap.get("enums", {}),
    }


def _build_system_context(ir: IR) -> dict | None:
    """Build system reg_map.sv context when 2+ distinct blocks are present.

    Collects distinct block names from register entries in order of first
    appearance, looks up their base_address from the blocks list, and assembles
    a context dict for the reg_map.sv.jinja template.

    Returns None when only a single block is present (no system assembly needed).

    Args:
        ir: Populated design IR with register_map set.

    Returns:
        Context dict with keys: project_name, blocks, data_width_bytes,
        endianness. Each block entry has: block_name, design_name,
        base_address. Returns None for single-block register maps.
    """
    regmap = ir.register_map
    if not regmap:
        return None

    # Collect distinct block names in order of first appearance
    seen: list[str] = []
    for reg in regmap.get("registers", []):
        bn = reg.get("block", "")
        if bn and bn not in seen:
            seen.append(bn)

    if len(seen) < 2:
        return None  # single block — no system assembly

    # Build a quick lookup from blocks list
    blocks_list = regmap.get("blocks", [])
    base_by_name: dict[str, str] = {}
    for blk in blocks_list:
        bn = blk.get("block_name", "")
        if bn:
            base_by_name[bn] = blk.get("base_address", "0x0")

    globals_dict = regmap.get("globals", {})
    project_name = globals_dict.get("project_name") or ir.design_name
    data_width_bits = globals_dict.get("data_width_bits", "32") or "32"
    try:
        data_width_bytes = int(str(data_width_bits)) // 8
    except (ValueError, TypeError):
        data_width_bytes = 4
    endianness_raw = globals_dict.get("endianness", "Little") or "Little"
    endianness = endianness_raw.strip().upper()

    block_entries = []
    for bn in seen:
        block_entries.append({
            "block_name":   bn,
            "design_name":  bn,  # lowercased in template for class prefix
            "base_address": base_by_name.get(bn, "0x0"),
        })

    return {
        "project_name":     project_name,
        "blocks":           block_entries,
        "data_width_bytes": data_width_bytes,
        "endianness":       endianness,
    }
