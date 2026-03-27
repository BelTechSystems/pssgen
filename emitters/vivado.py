# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""emitters/vivado.py — Vivado/XSIM artifact emitter.

Phase: v0
Layer: 5 (emitters)

Writes generated artifacts (.sv, .pss, build scripts) to disk for Vivado/XSIM flows.
"""
from agents.structure_gen import Artifact
from ir import IR
import os


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    """Write generated artifacts to the requested output directory.

    Args:
        ir: Parsed design IR (retained for interface stability).
        artifacts: Generated artifacts to write, including optional .pss models.
        out_dir: Destination directory path.

    Returns:
        List of paths that were written.
    """
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for artifact in artifacts:
        path = os.path.join(out_dir, artifact.filename)
        with open(path, "w") as f:
            f.write(artifact.content)
        written.append(path)
    return written
