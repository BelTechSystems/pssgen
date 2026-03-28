# ===========================================================
# FILE:         parser/systemverilog.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Stub SystemVerilog parser. Raises NotImplementedError until promoted to
#   a working implementation. Import path is stable; do not relocate.
#
# LAYER:        1 — parser
# PHASE:        v0
#
# FUNCTIONS:
#   parse(source_file, top_module)
#     Stub — raises NotImplementedError; tracked for v1 implementation.
#
# DEPENDENCIES:
#   Standard library:  none
#   Internal:          ir
#
# HISTORY:
#   v0    2026-03-27  SB  Stub placeholder; import path registered for v1
#
# ===========================================================
"""SystemVerilog parser stub (v1)."""

from ir import IR


def parse(source_file: str, top_module: str | None) -> IR:
    raise NotImplementedError(
        "SystemVerilog parsing is not implemented yet. Tracked in roadmap v1."
    )
