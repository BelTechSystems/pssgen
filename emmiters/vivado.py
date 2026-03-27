"""Vivado/XSIM emission target (v0). Writes .sv files and build.tcl."""
from agents.structure_gen import Artifact
from ir import IR
import os


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for artifact in artifacts:
        path = os.path.join(out_dir, artifact.filename)
        with open(path, "w") as f:
            f.write(artifact.content)
        written.append(path)
    return written
