"""
Orchestrator: drives the pipeline, owns the retry loop.
No UVM or PSS knowledge lives here — only coordination logic.
"""
from dataclasses import dataclass, field
from typing import Optional
import json, os

from ir import IR
from parser.verilog import parse as parse_verilog
from agents.structure_gen import generate
from checker import check
from emitters.vivado import emit as emit_vivado


@dataclass
class JobSpec:
    input_file: str
    top_module: Optional[str]
    out_dir: str
    sim_target: str
    max_retries: int
    dump_ir: bool = False
    verbose: bool = False


@dataclass
class OrchestratorResult:
    success: bool
    output_files: list[str] = field(default_factory=list)
    attempts: int = 0
    last_fail_reason: str = ""


def run(job: JobSpec) -> OrchestratorResult:
    # --- Parse ---
    ir = parse_verilog(job.input_file, job.top_module)
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

        artifacts = generate(ir, fail_reason=last_fail_reason)
        result = check(artifacts, job.sim_target)

        if result.passed:
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
