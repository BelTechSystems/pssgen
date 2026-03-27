"""PSS generator agent stub (v1)."""

from ir import IR
from agents.structure_gen import Artifact


def generate(ir: IR, fail_reason: str | None = None) -> list[Artifact]:
    raise NotImplementedError(
        "PSS generation is not implemented yet. Tracked in roadmap v1."
    )
