# ===========================================================
# FILE:         emitters/vivado.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Vivado/XSIM emission layer. Writes non-UVM artifacts (.pss, RAL .sv,
#   build.tcl) to the output directory. UVM .sv files are written by
#   scaffold_gen.generate_uvm_tb() to out_dir/tb/ before this emitter runs;
#   this layer skips any .sv that already exists under out_dir/tb/ (D-032).
#   Tcl simulation scripts are written to scripts/vivado/ per D-029.
#
# LAYER:        5 — emitters
# PHASE:        v0
#
# FUNCTIONS:
#   emit(ir, artifacts, out_dir)
#     Write non-UVM artifacts to out_dir; return list of written file paths.
#     Tcl scripts route to out_dir/scripts/vivado/.
#     UVM .sv files already written to out_dir/tb/ are skipped.
#
# DEPENDENCIES:
#   Standard library:  os
#   Internal:          agents.structure_gen, ir
#
# HISTORY:
#   v0    2026-03-27  SB  Initial implementation; verbatim artifact write-out
#   v4b   2026-04-03  SB  UTF-8 encoding on file writes (RAL templates use non-ASCII)
#   v5b   2026-04-10  SB  Route .tcl artifacts to scripts/vivado/ per D-029
#   v6b   2026-04-14  SB  Skip UVM .sv already written to tb/ by scaffold_gen (D-032)
#
# ===========================================================
"""emitters/vivado.py — Vivado/XSIM artifact emitter.

Phase: v0
Layer: 5 (emitters)

Writes non-UVM artifacts (.pss, RAL .sv, build scripts) to disk for Vivado/XSIM flows.
UVM .sv files are written by scaffold_gen.generate_uvm_tb() to out_dir/tb/ before this
emitter runs; any .sv artifact already present under out_dir/tb/ is skipped here to
avoid duplicating work (Option B: existence-check, D-032). Tcl simulation scripts are
placed under scripts/vivado/ within out_dir per D-029.
"""
from agents.structure_gen import Artifact
from ir import IR
import os


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    """Write non-UVM generated artifacts to the requested output directory.

    UVM .sv files are already written to ``out_dir/tb/`` by
    ``scaffold_gen.generate_uvm_tb()`` before this function is called.  Any
    ``.sv`` artifact whose filename already exists under ``out_dir/tb/`` is
    therefore skipped here — D-032 design choice: existence-check (Option B)
    keeps the Artifact dataclass unchanged and avoids churn in callers/tests.

    Tcl scripts (``.tcl``) are written to ``out_dir/scripts/vivado/``.
    All other artifacts (``.pss``, RAL ``.sv``, etc.) are written flat into
    ``out_dir``.

    Args:
        ir: Parsed design IR (retained for interface stability).
        artifacts: Generated artifacts to write, including optional .pss models.
        out_dir: Destination directory path.

    Returns:
        List of paths that were written (already-written UVM files excluded).
    """
    os.makedirs(out_dir, exist_ok=True)
    scripts_dir = os.path.join(out_dir, "scripts", "vivado")
    tb_dir = os.path.join(out_dir, "tb")
    written = []
    for artifact in artifacts:
        # Skip UVM .sv files already written to tb/ by generate_uvm_tb().
        # Existence-check chosen over adding a source field to Artifact because
        # it avoids touching the dataclass and all its callers (D-032, Option B).
        if artifact.filename.endswith(".sv"):
            tb_path = os.path.join(tb_dir, artifact.filename)
            if os.path.exists(tb_path):
                continue

        if artifact.filename.endswith(".tcl"):
            os.makedirs(scripts_dir, exist_ok=True)
            path = os.path.join(scripts_dir, artifact.filename)
        else:
            path = os.path.join(out_dir, artifact.filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(artifact.content)
        written.append(path)
    return written
