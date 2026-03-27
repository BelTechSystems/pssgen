"""Generic C emission target stub (v2)."""

from ir import IR
from agents.structure_gen import Artifact


def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    raise NotImplementedError(
        "Generic C emission target not yet implemented. Tracked in roadmap v2."
    )
