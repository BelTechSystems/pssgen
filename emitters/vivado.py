# ===========================================================
# FILE:         emitters/vivado.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Vivado/XSIM emission layer. Writes all generated artifacts (.sv, .pss,
#   build.tcl) to the output directory. Tcl simulation scripts are written
#   to scripts/vivado/ within out_dir per D-029 directory conventions.
#
# LAYER:        5 — emitters
# PHASE:        v0
#
# FUNCTIONS:
#   emit(ir, artifacts, out_dir)
#     Write all artifacts to out_dir; return list of written file paths.
#     Tcl scripts route to out_dir/scripts/vivado/.
#
# DEPENDENCIES:
#   Standard library:  os
#   Internal:          agents.structure_gen, ir
#
# HISTORY:
#   v0    2026-03-27  SB  Initial implementation; verbatim artifact write-out
#   v4b   2026-04-03  SB  UTF-8 encoding on file writes (RAL templates use non-ASCII)
#   v5b   2026-04-10  SB  Route .tcl artifacts to scripts/vivado/ per D-029
#
# ===========================================================
"""emitters/vivado.py — Vivado/XSIM artifact emitter.

Phase: v0
Layer: 5 (emitters)

Writes generated artifacts (.sv, .pss, build scripts) to disk for Vivado/XSIM flows.
Tcl simulation scripts are placed under scripts/vivado/ within out_dir per D-029.
"""
from agents.structure_gen import Artifact
from ir import IR
import os


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    """Write generated artifacts to the requested output directory.

    Tcl scripts (.tcl) are written to ``out_dir/scripts/vivado/`` rather than
    directly into ``out_dir``. All other artifacts are written flat into ``out_dir``.

    Args:
        ir: Parsed design IR (retained for interface stability).
        artifacts: Generated artifacts to write, including optional .pss models.
        out_dir: Destination directory path.

    Returns:
        List of paths that were written.
    """
    os.makedirs(out_dir, exist_ok=True)
    scripts_dir = os.path.join(out_dir, "scripts", "vivado")
    written = []
    for artifact in artifacts:
        if artifact.filename.endswith(".tcl"):
            os.makedirs(scripts_dir, exist_ok=True)
            path = os.path.join(scripts_dir, artifact.filename)
        else:
            path = os.path.join(out_dir, artifact.filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(artifact.content)
        written.append(path)
    return written
