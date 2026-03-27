# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""orchestrator.py — Pipeline coordinator and retry owner.

Phase: v0
Layer: Coordination (above Layers 1-5)

Coordinates parse, generation, checking, and emission. Owns retry logic and
injects checker failure reasons into subsequent generation attempts.
"""
from dataclasses import dataclass, field
from typing import Optional
import json, os

from ir import IR
from parser.dispatch import parse_source
from agents.structure_gen import Artifact, generate
from agents.pss_gen import generate_pss
from checkers.verifier import check
from emitters.vivado import emit as emit_vivado


@dataclass
class JobSpec:
    """Execution parameters for a single orchestrator run.

    Attributes:
        input_file: Path to the HDL input file.
        top_module: Optional explicit top module name.
        out_dir: Output directory for emitted artifacts.
        sim_target: Simulator target name (for example, "vivado").
        max_retries: Maximum checker-guided regeneration attempts.
        dump_ir: Whether to write an `ir.json` snapshot into `out_dir`.
        no_llm: Whether generation should run in template-only mode.
        verbose: Whether to print orchestrator progress logs.
    """
    input_file: str
    top_module: Optional[str]
    out_dir: str
    sim_target: str
    max_retries: int
    dump_ir: bool = False
    no_llm: bool = False
    verbose: bool = False


@dataclass
class OrchestratorResult:
    """Outcome of an orchestrator run.

    Attributes:
        success: Whether generation and checking completed successfully.
        output_files: List of emitted output file paths.
        attempts: Number of generation attempts performed.
        last_fail_reason: Final checker failure reason if not successful.
    """
    success: bool
    output_files: list[str] = field(default_factory=list)
    attempts: int = 0
    last_fail_reason: str = ""


def run(job: JobSpec) -> OrchestratorResult:
    """Run the end-to-end generation and checker loop.

    Args:
        job: Job configuration including retry, emission, and no-LLM mode.

    Returns:
        OrchestratorResult describing success, outputs, attempts, and failure.
    """
    # --- Parse ---
    ir = parse_source(job.input_file, job.top_module)
    ir.emission_target = job.sim_target
    ir.output_dir = job.out_dir

    if job.dump_ir:
        os.makedirs(job.out_dir, exist_ok=True)
        with open(os.path.join(job.out_dir, "ir.json"), "w") as f:
            json.dump(ir.__dict__, f, indent=2, default=lambda o: o.__dict__)

    if job.verbose:
        print(f"[orchestrator] IR populated: {ir.design_name}, {len(ir.ports)} ports")

    # --- Orchestrator retry loop ---
    last_fail_reason: Optional[str] = None
    for attempt in range(1, job.max_retries + 1):
        if job.verbose:
            print(f"[orchestrator] Attempt {attempt}/{job.max_retries}")

        artifacts = generate(ir, fail_reason=last_fail_reason, no_llm=job.no_llm)
        pss_model = generate_pss(ir, fail_reason=last_fail_reason, no_llm=job.no_llm)
        artifacts.append(Artifact(filename=f"{ir.design_name}.pss", content=pss_model))
        result = check(artifacts, job.sim_target)

        if result.passed:
            if job.verbose:
                print(f"[orchestrator] Checker passed all tiers; tier-1 structural checks passed")
            output_files = emit_vivado(ir, artifacts, job.out_dir)
            return OrchestratorResult(
                success=True,
                output_files=output_files,
                attempts=attempt,
            )

        last_fail_reason = result.reason
        if job.verbose:
            print(f"[orchestrator] Checker tier {result.tier} fail: {result.reason}")

    return OrchestratorResult(
        success=False,
        attempts=job.max_retries,
        last_fail_reason=last_fail_reason or "unknown",
    )
