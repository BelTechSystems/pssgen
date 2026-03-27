"""Questa emission target stub (v2)."""

from ir import IR
from agents.structure_gen import Artifact


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    raise NotImplementedError(
        "Questa emission target not yet implemented. Use --sim vivado. Tracked in roadmap v2."
    )
