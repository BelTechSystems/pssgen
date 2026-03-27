# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""emitters/questa.py — Questa/QuestaSim artifact emitter.

Phase: v2c
Layer: 5 (emitters)

Writes generated artifacts (.sv, .pss) to disk for Questa/QuestaSim flows
and renders a Makefile from the Questa Makefile template. The Makefile uses
vlog for compilation and vsim for simulation, matching Questa's CLI interface.
"""
import os

from jinja2 import Environment, FileSystemLoader

from agents.structure_gen import Artifact
from ir import IR


_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "uvm")
_TEMPLATE_NAME = "build_questa.mk.jinja"


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    """Emit Questa-compatible UVM artifacts.

    Writes all .sv and .pss artifacts to out_dir, then renders and writes a
    Makefile using the Questa Makefile template. The build.tcl artifact
    produced for Vivado flows is intentionally excluded — Questa uses make.

    Args:
        ir: Populated design IR.
        artifacts: Checker-validated artifact list.
        out_dir: Target output directory.

    Returns:
        List of written file paths.
    """
    os.makedirs(out_dir, exist_ok=True)

    written: list[str] = []
    sv_filenames: list[str] = []

    for artifact in artifacts:
        # Emit .sv and .pss artifacts; skip Vivado-specific build scripts.
        if artifact.filename.endswith(".sv") or artifact.filename.endswith(".pss"):
            path = os.path.join(out_dir, artifact.filename)
            with open(path, "w") as fh:
                fh.write(artifact.content)
            written.append(path)
            if artifact.filename.endswith(".sv"):
                sv_filenames.append(artifact.filename)

    # Render Questa Makefile.
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        keep_trailing_newline=True,
    )
    template = env.get_template(_TEMPLATE_NAME)
    makefile_content = template.render(
        design_name=ir.design_name,
        sv_files=sv_filenames,
    )

    makefile_path = os.path.join(out_dir, "Makefile")
    with open(makefile_path, "w") as fh:
        fh.write(makefile_content)
    written.append(makefile_path)

    return written
