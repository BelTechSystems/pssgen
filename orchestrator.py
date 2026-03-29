# ===========================================================
# FILE:         orchestrator.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Coordinates the parse, generation, checking, and emission pipeline.
#   Owns the retry loop and injects checker failure reasons into subsequent
#   generation attempts. Resolves intent and .req context files by convention
#   or explicit flag and generates scaffold files when requested.
#
# LAYER:        Coordination (above Layers 1–5)
# PHASE:        v0
#
# FUNCTIONS:
#   run(job)
#     Execute the end-to-end generation and checker loop; return OrchestratorResult.
#   _resolve_emitter(sim_target)
#     Return the emit callable for the requested simulator target.
#   _write_req_skeleton(req_path, ir, intent_result)
#     Write a minimal .req skeleton extracted from intent requirement IDs.
#
# DEPENDENCIES:
#   Standard library:  dataclasses, typing, json, os
#   Internal:          ir, parser.dispatch, parser.intent_parser, parser.req_parser,
#                      parser.context, agents.structure_gen, agents.pss_gen,
#                      agents.scaffold_gen, checkers.verifier,
#                      emitters.vivado, emitters.questa, emitters.generic_c
#
# HISTORY:
#   v0    2026-03-27  SB  Initial implementation; parse–generate–check–emit loop
#   v1b   2026-03-27  SB  Added PSS model generation via agents.pss_gen
#   v2a   2026-03-27  SB  Added --intent / ir.pss_intent propagation
#   v2b   2026-03-27  SB  Added generic C emitter dispatch via _resolve_emitter
#   v2c   2026-03-27  SB  Added Questa emitter dispatch
#   v3a   2026-03-28  SB  Intent/req auto-detection, scaffold generation, verbose context logging
#   v3b   2026-03-28  SB  Gap analysis wiring, coverage_labels, gap_report_path in OrchestratorResult
#
# ===========================================================
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
from parser.intent_parser import parse_intent
from parser.req_parser import parse_req
from parser.context import resolve_context_files
from agents.structure_gen import Artifact, generate
from agents.pss_gen import generate_pss, _build_coverage_labels
from agents.scaffold_gen import generate_intent_scaffold, generate_req_scaffold
from agents.gap_agent import analyse_gaps, write_gap_report, format_console_summary
from checkers.verifier import check
from emitters.vivado import emit as emit_vivado
from emitters.questa import emit as emit_questa
from emitters.generic_c import emit as emit_generic_c


@dataclass
class JobSpec:
    """Execution parameters for a single orchestrator run.

    Attributes:
        input_file: Path to the HDL input file.
        top_module: Optional explicit top module name.
        out_dir: Output directory for emitted artifacts.
        sim_target: Simulator target name ("vivado", "questa", or "generic").
        max_retries: Maximum checker-guided regeneration attempts.
        intent_file: Optional explicit path to .intent file (overrides convention).
        dump_ir: Whether to write an `ir.json` snapshot into `out_dir`.
        no_llm: Whether generation should run in template-only mode.
        verbose: Whether to print orchestrator progress logs.
        req_file: Optional explicit path to .req file (overrides convention).
        no_intent: If True, suppress auto-detection of <stem>.intent.
        no_req: If True, suppress auto-detection of <stem>.req.
        scaffold: If True, generate _generated.intent and _generated.req in out_dir.
        coverage_loop: Stub — raises NotImplementedError when set; reserved for v3c.
    """
    input_file: str
    top_module: Optional[str]
    out_dir: str
    sim_target: str
    max_retries: int
    intent_file: Optional[str] = None
    dump_ir: bool = False
    no_llm: bool = False
    verbose: bool = False
    req_file: Optional[str] = None
    no_intent: bool = False
    no_req: bool = False
    scaffold: bool = False
    coverage_loop: Optional[int] = None


@dataclass
class OrchestratorResult:
    """Outcome of an orchestrator run.

    Attributes:
        success: Whether generation and checking completed successfully.
        output_files: List of emitted output file paths.
        attempts: Number of generation attempts performed.
        last_fail_reason: Final checker failure reason if not successful.
        gap_report_path: Path to the written gap report, or None if not produced.
    """
    success: bool
    output_files: list[str] = field(default_factory=list)
    attempts: int = 0
    last_fail_reason: str = ""
    gap_report_path: Optional[str] = None


def _resolve_emitter(sim_target: str):
    """Return the emit callable for the requested simulator target.

    Args:
        sim_target: One of "vivado", "questa", or "generic".

    Returns:
        Callable matching the emitter interface:
        ``emit(ir, artifacts, out_dir) -> list[str]``.

    Raises:
        ValueError: If sim_target is not a recognised target.
    """
    dispatch = {
        "vivado":  emit_vivado,
        "questa":  emit_questa,
        "generic": emit_generic_c,
    }
    if sim_target not in dispatch:
        raise ValueError(
            f"Unknown sim_target '{sim_target}'. "
            f"Valid targets: {sorted(dispatch)}"
        )
    return dispatch[sim_target]


def _write_req_skeleton(req_path: str, ir: IR, intent_result) -> None:
    """Write a minimal .req skeleton extracted from intent requirement IDs.

    Called only when no .req file exists and the intent contains req IDs.
    The file is never overwritten — callers must check existence first.

    Args:
        req_path: Destination path for the new .req file.
        ir: Populated IR (used for design name in comments).
        intent_result: IntentParseResult containing req_ids.
    """
    lines = [
        "# Auto-extracted requirements skeleton from intent file.",
        f"# Design: {ir.design_name}",
        "# Human review required for all entries.",
        "",
    ]
    for rid in intent_result.req_ids:
        lines.append(f"[{rid}] [GENERATED] Statement — human review required.")
        lines.append("  verification: simulation")
        lines.append("")
    with open(req_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run(job: JobSpec) -> OrchestratorResult:
    """Run the end-to-end generation and checker loop.

    Args:
        job: Job configuration including retry, emission, and no-LLM mode.

    Returns:
        OrchestratorResult describing success, outputs, attempts, and failure.

    Raises:
        NotImplementedError: If coverage_loop is set (reserved for v3c).
    """
    # --- coverage_loop guard (v3c stub) ---
    if job.coverage_loop is not None:
        raise NotImplementedError("--coverage-loop not implemented; see v3c")

    # --- Parse ---
    ir = parse_source(job.input_file, job.top_module)
    ir.emission_target = job.sim_target
    ir.output_dir = job.out_dir

    # --- Resolve context files (intent + req) via convention or explicit flags ---
    intent_path, req_path, should_extract = resolve_context_files(
        input_file=job.input_file,
        intent_flag=job.intent_file,
        req_flag=job.req_file,
        no_intent=job.no_intent,
        no_req=job.no_req,
    )

    # Determine how intent was located for verbose reporting
    if intent_path is not None:
        intent_source = "explicit" if job.intent_file else "auto-detected"
    else:
        intent_source = "none"

    # Determine how req was located for verbose reporting
    intent_result = None
    if intent_path:
        intent_result = parse_intent(intent_path)
        ir.pss_intent = open(intent_path, "r", encoding="utf-8").read()
        ir.requirement_ids = intent_result.req_ids
        ir.requirement_schemes = intent_result.req_schemes
        ir.intent_waivers = intent_result.waivers

    req_result = None
    req_source = "none"
    if req_path:
        req_result = parse_req(req_path)
        req_source = "explicit" if job.req_file else "auto-detected"
    elif should_extract and intent_result is not None and intent_result.req_ids:
        # Auto-extract: write a .req skeleton next to the input file, never overwrite
        stem = os.path.splitext(os.path.basename(job.input_file))[0]
        extracted_req_path = os.path.join(
            os.path.dirname(os.path.abspath(job.input_file)),
            f"{stem}.req"
        )
        if not os.path.exists(extracted_req_path):
            _write_req_skeleton(extracted_req_path, ir, intent_result)
        req_source = "extracted"

    if job.verbose:
        print(f"[orchestrator] Intent: {intent_path} ({intent_source})")
        print(f"[orchestrator] Req: {req_path} ({req_source})")
        if intent_result:
            print(
                f"[orchestrator] Detected schemes: "
                f"{', '.join(intent_result.req_schemes) or 'none'}"
            )
            print(
                f"[orchestrator] Requirement IDs found: "
                f"{len(intent_result.req_ids)}"
            )
            print(f"[orchestrator] Waivers: {len(intent_result.waivers)}")

    # --- Scaffold generation (--scaffold flag) ---
    if job.scaffold:
        os.makedirs(job.out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(job.input_file))[0]
        intent_scaffold_path = os.path.join(
            job.out_dir, f"{stem}_generated.intent"
        )
        req_scaffold_path = os.path.join(
            job.out_dir, f"{stem}_generated.req"
        )
        # Never overwrite existing scaffolds
        if not os.path.exists(intent_scaffold_path):
            generate_intent_scaffold(ir, intent_result, intent_scaffold_path)
            if job.verbose:
                print(f"[orchestrator] Wrote intent scaffold: {intent_scaffold_path}")
        else:
            if job.verbose:
                print(
                    f"[orchestrator] Intent scaffold already exists, "
                    f"skipping: {intent_scaffold_path}"
                )
        if not os.path.exists(req_scaffold_path):
            generate_req_scaffold(ir, intent_result, req_scaffold_path)
            if job.verbose:
                print(f"[orchestrator] Wrote req scaffold: {req_scaffold_path}")
        else:
            if job.verbose:
                print(
                    f"[orchestrator] Req scaffold already exists, "
                    f"skipping: {req_scaffold_path}"
                )

    # Legacy verbose log for intent (kept for test compatibility)
    if job.verbose and intent_path:
        print(f"[orchestrator] Loaded intent file: {intent_path}")

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
        pss_model = generate_pss(
            ir,
            fail_reason=last_fail_reason,
            no_llm=job.no_llm,
            intent_result=intent_result,
        )
        artifacts.append(Artifact(filename=f"{ir.design_name}.pss", content=pss_model))

        # --- Gap analysis (v3b) ---
        gap_report_path: Optional[str] = None
        if intent_result is not None or req_result is not None:
            stem = os.path.splitext(os.path.basename(job.input_file))[0]
            coverage_labels = _build_coverage_labels(ir, intent_result)
            gap_report = analyse_gaps(ir, intent_result, req_result, coverage_labels)
            gap_report.input_file = job.input_file
            gap_report.intent_path = intent_path or ""
            gap_report.req_path = req_path or ""
            os.makedirs(job.out_dir, exist_ok=True)
            gap_report_path = os.path.join(
                job.out_dir, f"{stem}_gap_report.txt"
            )
            write_gap_report(gap_report, gap_report_path)
            summary = format_console_summary(gap_report)
            print(f"{summary} -> {os.path.basename(gap_report_path)}")
            if job.verbose and gap_report.errors:
                for e in gap_report.errors:
                    print(f"  [ERROR] {e['req_id']}: {e['message']}")

        result = check(artifacts, job.sim_target)

        if result.passed:
            if job.verbose:
                print(f"[orchestrator] Checker passed all tiers; tier-1 structural checks passed")
            emitter = _resolve_emitter(job.sim_target)
            output_files = emitter(ir, artifacts, job.out_dir)
            return OrchestratorResult(
                success=True,
                output_files=output_files,
                attempts=attempt,
                gap_report_path=gap_report_path,
            )

        last_fail_reason = result.reason
        if job.verbose:
            print(f"[orchestrator] Checker tier {result.tier} fail: {result.reason}")

    return OrchestratorResult(
        success=False,
        attempts=job.max_retries,
        last_fail_reason=last_fail_reason or "unknown",
    )
