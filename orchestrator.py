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
#   Internal:          ir, parser.dispatch, parser.intent_parser, parser.req_parser, parser.vplan_parser,
#                      parser.context, agents.structure_gen, agents.pss_gen,
#                      agents.scaffold_gen, agents.gap_agent, agents.coverage_reader,
#                      agents.closure_gen, agents.datasheet_gen, checkers.verifier,
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
#   v3c-a 2026-03-29  SB  Added coverage_db stub field to JobSpec
#   v3c-b 2026-03-29  SB  Coverage closure loop, _run_closure_loop, closure_passes/script in result
#   v4a   2026-04-03  SB  Added reg_map_file to JobSpec; register map loading + ir.register_map wiring
#   v4b   2026-04-03  SB  Wired generate_ral; RAL artifacts appended to pipeline after regmap load
#   v4c      2026-04-05  SB  register_maps_list multi-file merge from pssgen.toml
#   v5a-prep 2026-04-06  SB  .req is optional; inline_requirements flow through intent_result (D-025)
#   v5a      2026-04-08  SB  Wired generate_datasheet; DATASHEET.md added to output_files (D-026)
#   v6a      2026-04-12  SB  Replaced parse_req + parse_intent with parse_vplan (OI-30, D-031)
#   v6b      2026-04-14  SB  Wire generate_uvm_tb into pipeline (D-032)
#   v6c      2026-04-16  SB  Wire --collect-results (OI-29)
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
from parser.vplan_parser import parse_vplan
from parser.context import resolve_context_files, resolve_regmap_file
from parser.regmap_parser import parse_regmap
from agents.structure_gen import Artifact, generate
from agents.pss_gen import generate_pss, _build_coverage_labels
from agents.scaffold_gen import generate_intent_scaffold, generate_req_scaffold, generate_uvm_tb
from agents.gap_agent import analyse_gaps, update_gaps_from_coverage, write_gap_report, format_console_summary
from agents.coverage_reader import read_coverage_xml
from agents.closure_gen import generate_closure_script
from checkers.verifier import check
from agents.ral_gen import generate_ral
from agents.datasheet_gen import generate_datasheet
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
        coverage_db: Stub — coverage database path; reserved for v3c.
        reg_map_file: Optional explicit path to register map .xlsx or .intent file.
        register_maps_list: Optional list of {file, base_address} dicts for multi-file mode.
        collect_results: If True, parse sim_log and write RTL results back to the VPR.
        sim_log: Path to xsim.log; required when collect_results is True.
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
    coverage_db: Optional[str] = None
    reg_map_file: Optional[str] = None
    register_maps_list: Optional[list] = None
    collect_results: bool = False
    sim_log: Optional[str] = None


@dataclass
class OrchestratorResult:
    """Outcome of an orchestrator run.

    Attributes:
        success: Whether generation and checking completed successfully.
        output_files: List of emitted output file paths.
        attempts: Number of generation attempts performed.
        last_fail_reason: Final checker failure reason if not successful.
        gap_report_path: Path to the written gap report, or None if not produced.
        closure_passes: Number of coverage closure iterations performed.
        closure_script_path: Path to the last closure script written, or None.
    """
    success: bool
    output_files: list[str] = field(default_factory=list)
    attempts: int = 0
    last_fail_reason: str = ""
    gap_report_path: Optional[str] = None
    closure_passes: int = 0
    closure_script_path: Optional[str] = None
    datasheet_path: Optional[str] = None


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


def _run_closure_loop(
    job: JobSpec,
    ir: IR,
    gap_report,
    gap_report_path: Optional[str],
    intent_result,
    base_result: "OrchestratorResult",
) -> "OrchestratorResult":
    """Run the coverage-guided closure loop after the main pipeline.

    Reads coverage XML each pass, updates the gap report, regenerates the
    PSS model with uncovered labels as context, and writes a closure script
    the engineer can run to advance to the next pass.

    If ``job.coverage_db`` is not set: warns, generates pass-1 script, and
    returns immediately with ``closure_passes=0``.

    Args:
        job: Job configuration (coverage_loop, coverage_db, sim_target, etc.).
        ir: Populated design IR.
        gap_report: GapReport from the main pipeline, or None.
        gap_report_path: Path where gap report is written, or None.
        intent_result: IntentParseResult for PSS regeneration context.
        base_result: OrchestratorResult from the main pipeline loop.

    Returns:
        Updated OrchestratorResult with closure_passes and closure_script_path.
    """
    from agents.gap_agent import GapReport as _GapReport

    # Ensure we always have a GapReport to work with
    if gap_report is None:
        gap_report = _GapReport(design_name=ir.design_name)

    # If no closure DB provided: warn, generate pass-1 script, return
    if not job.coverage_db:
        print(
            "[pssgen] --coverage-loop requires --coverage-db.\n"
            "         Generate coverage XML by running your simulator,\n"
            "         then re-run with --coverage-db <path>."
        )
        script_path = generate_closure_script(
            ir=ir,
            sim_target=job.sim_target,
            pass_number=1,
            gap_report=gap_report,
            out_dir=job.out_dir,
        )
        if job.verbose:
            print(f"[orchestrator] Closure script written: {script_path}")
        base_result.closure_passes = 0
        base_result.closure_script_path = script_path
        return base_result

    # ---- Main closure loop ----
    script_path: Optional[str] = None
    max_passes: int = job.coverage_loop  # type: ignore[assignment]

    for pass_num in range(1, max_passes + 1):
        if job.verbose:
            print(f"[orchestrator] Closure pass {pass_num}/{max_passes}")

        # 1. Read coverage XML and update gap report
        cov_result = read_coverage_xml(job.coverage_db)
        for warn in cov_result.parse_warnings:
            print(f"[pssgen] Coverage XML warning: {warn}")

        gap_report = update_gaps_from_coverage(gap_report, cov_result)
        gap_report.coverage_pass = pass_num

        # 2. Regenerate PSS model with uncovered labels as context
        still_missed = gap_report.missed_labels + gap_report.uncovered_labels
        if still_missed:
            fail_reason = f"Uncovered: {', '.join(still_missed[:10])}"
            if len(still_missed) > 10:
                fail_reason += f" (+{len(still_missed) - 10} more)"
        else:
            # All labels covered — build a success message
            fail_reason = None

        pss_model = generate_pss(
            ir,
            fail_reason=fail_reason,
            no_llm=job.no_llm,
            intent_result=intent_result,
        )
        # Write updated .pss file
        pss_file = os.path.join(job.out_dir, f"{ir.design_name}.pss")
        os.makedirs(job.out_dir, exist_ok=True)
        with open(pss_file, "w", encoding="utf-8") as fh:
            fh.write(pss_model)

        # 3. Generate closure script for this pass
        script_path = generate_closure_script(
            ir=ir,
            sim_target=job.sim_target,
            pass_number=pass_num,
            gap_report=gap_report,
            out_dir=job.out_dir,
        )

        # 4. Write updated gap report
        if gap_report_path:
            write_gap_report(gap_report, gap_report_path)
        elif job.out_dir:
            stem = os.path.splitext(os.path.basename(job.input_file))[0]
            gap_report_path = os.path.join(job.out_dir, f"{stem}_gap_report.txt")
            write_gap_report(gap_report, gap_report_path)

        # 5. Console summary
        print(format_console_summary(gap_report))
        if job.verbose:
            print(f"[orchestrator] Closure script written: {script_path}")

        # Early exit if all errors closed
        if not gap_report.errors:
            if job.verbose:
                print("[orchestrator] All requirement gaps closed — closure complete.")
            break

    base_result.closure_passes = pass_num  # type: ignore[possibly-undefined]
    base_result.closure_script_path = script_path
    if gap_report_path:
        base_result.gap_report_path = gap_report_path
    return base_result


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

    # --- Resolve context files (intent + req) via convention or explicit flags ---
    # When no_req is set, suppress even a toml-specified req_file so that
    # --no-req is an unconditional override (D-025: .req is optional).
    effective_req_flag = None if job.no_req else job.req_file
    intent_path, req_path, should_extract = resolve_context_files(
        input_file=job.input_file,
        intent_flag=job.intent_file,
        req_flag=effective_req_flag,
        no_intent=job.no_intent,
        no_req=job.no_req,
    )

    # Determine how intent/vplan was located for verbose reporting
    if intent_path is not None:
        intent_source = "explicit" if job.intent_file else "auto-detected"
    else:
        intent_source = "none"

    # VPR path (.xlsx) takes precedence; fall back to legacy .intent / .req
    vplan_result = None
    intent_result = None
    req_result = None
    req_source = "none"

    vplan_path = intent_path  # resolve_context_files returns vplan via intent slot
    if vplan_path and vplan_path.endswith(".xlsx"):
        vplan_result = parse_vplan(vplan_path)
        intent_result = vplan_result
        req_result = vplan_result
        ir.requirement_ids = vplan_result.req_ids
        ir.requirement_schemes = vplan_result.req_schemes
        ir.intent_waivers = vplan_result.intent_waivers
        req_source = "explicit" if job.intent_file else "auto-detected"
    else:
        # Legacy .intent / .req path
        if intent_path:
            intent_result = parse_intent(intent_path)
            ir.pss_intent = open(intent_path, "r", encoding="utf-8").read()
            ir.requirement_ids = intent_result.req_ids
            ir.requirement_schemes = intent_result.req_schemes
            ir.intent_waivers = intent_result.waivers

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
        if vplan_result is not None:
            print(f"[orchestrator] VPR: {vplan_path} ({intent_source})")
            print(
                f"[orchestrator] Detected schemes: "
                f"{', '.join(vplan_result.req_schemes) or 'none'}"
            )
            print(
                f"[orchestrator] Requirement IDs found: "
                f"{len(vplan_result.req_ids)}"
            )
            print(f"[orchestrator] Waivers: {len(vplan_result.waivers)}")
        else:
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

    # --- Register map loading (v4a) ---
    regmap_path = resolve_regmap_file(job.input_file, job.reg_map_file)
    if regmap_path:
        if job.verbose and regmap_path.endswith(".xlsx"):
            from parser.regmap_parser import detect_regmap_format
            fmt = detect_regmap_format(regmap_path)
            print(f"[orchestrator] Register map format: {fmt}")
        ir.register_map = parse_regmap(regmap_path)
        if job.verbose:
            regs = ir.register_map.get("registers", [])
            blocks = ir.register_map.get("blocks", [])
            total_fields = sum(len(r.get("fields", [])) for r in regs)
            regmap_source = "explicit" if job.reg_map_file else "auto-detected"
            print(
                f"[orchestrator] Register map loaded ({regmap_source}): "
                f"{len(regs)} registers, {total_fields} fields across "
                f"{len(blocks)} block(s)"
            )
    elif intent_result is not None and not job.reg_map_file:
        # Fall back to register map: section in intent file if present
        regmap_sections = {k: v for k, v in intent_result.sections.items()
                           if k.lower().strip() == "register map"}
        if regmap_sections:
            section_lines = next(iter(regmap_sections.values()))
            section_content = "register map:\n" + "\n".join(f"  {ln}" for ln in section_lines)
            from parser.regmap_parser import _parse_intent_regmap
            ir.register_map = _parse_intent_regmap(section_content)
            if job.verbose and ir.register_map:
                regs = ir.register_map.get("registers", [])
                print(
                    f"[orchestrator] Register map parsed from intent file: "
                    f"{len(regs)} register(s) (Tier 2)"
                )

    # --- Multi-file register map merge (pssgen.toml [[register_maps]]) ---
    if job.register_maps_list:
        merged: dict = {"globals": {}, "blocks": [], "registers": [], "enums": {}}
        first = True
        for entry in job.register_maps_list:
            block_data = parse_regmap(entry["file"])
            # Apply per-entry base_address override to all blocks
            if entry.get("base_address"):
                for blk in block_data.get("blocks", []):
                    blk["base_address"] = entry["base_address"]
            if first:
                merged["globals"] = block_data.get("globals", {})
                first = False
            merged["blocks"].extend(block_data.get("blocks", []))
            merged["registers"].extend(block_data.get("registers", []))
            for ename, evals in block_data.get("enums", {}).items():
                if ename not in merged["enums"]:
                    merged["enums"][ename] = evals
        ir.register_map = merged
        if job.verbose:
            regs = merged.get("registers", [])
            blocks = merged.get("blocks", [])
            total_fields = sum(len(r.get("fields", [])) for r in regs)
            print(
                f"[orchestrator] Multi-file register maps merged: "
                f"{len(regs)} registers, {total_fields} fields across "
                f"{len(blocks)} block(s)"
            )

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

    if job.dump_ir:
        os.makedirs(job.out_dir, exist_ok=True)
        with open(os.path.join(job.out_dir, "ir.json"), "w") as f:
            json.dump(ir.__dict__, f, indent=2, default=lambda o: o.__dict__)

    # --- UVM testbench generation (D-032) ---
    # generate_uvm_tb() is safe to call on every run:
    # its never-overwrite contract skips existing files.
    uvm_paths = generate_uvm_tb(
        ir=ir,
        vplan_result=vplan_result,
        out_dir=job.out_dir,
    )
    if job.verbose:
        print(
            f"[orchestrator] UVM testbench: "
            f"{len(uvm_paths)} files → {job.out_dir}/tb/"
        )

    if job.verbose:
        print(f"[orchestrator] IR populated: {ir.design_name}, {len(ir.ports)} ports")

    # --- Collect simulation results and write back to VPR (OI-29) ---
    if job.collect_results:
        from agents.results_collector import (
            parse_xsim_log,
            write_vpr_results,
            generate_gap_report_json,
        )
        if not job.sim_log:
            print("[pssgen] --collect-results requires --sim-log <path>")
            return OrchestratorResult(
                success=False,
                last_fail_reason="--sim-log not provided",
            )
        sim_result = parse_xsim_log(job.sim_log)
        if job.verbose:
            print(
                f"[orchestrator] Sim result: "
                f"{'PASS' if sim_result.passed else 'FAIL'} "
                f"({sim_result.uvm_errors} errors, "
                f"{sim_result.uvm_warnings} warnings)"
            )
        gap_json_path: Optional[str] = None
        if vplan_path and vplan_path.endswith(".xlsx"):
            rows_updated = write_vpr_results(
                vplan_path=vplan_path,
                sim_result=sim_result,
            )
            if job.verbose:
                print(f"[orchestrator] VPR updated: {rows_updated} rows")
            os.makedirs(job.out_dir, exist_ok=True)
            gap_json_path = os.path.join(job.out_dir, "gap_report.json")
            generate_gap_report_json(
                vplan_path=vplan_path,
                sim_result=sim_result,
                out_path=gap_json_path,
            )
            print(f"[pssgen] Gap report: {gap_json_path}")
        return OrchestratorResult(
            success=sim_result.passed,
            output_files=[job.sim_log],
            gap_report_path=gap_json_path,
        )

    # --- Orchestrator retry loop ---
    last_fail_reason: Optional[str] = None
    gap_report = None  # populated inside loop if intent/req files present
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

        if ir.register_map is not None:
            ral_artifacts = generate_ral(ir, no_llm=job.no_llm)
            artifacts.extend(ral_artifacts)
            if job.verbose:
                print(
                    f"[orchestrator] RAL artifacts generated:"
                    f" {len(ral_artifacts)} files"
                )

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
            # UVM tb/ files were written before the retry loop; include in output list.
            output_files = list(uvm_paths) + output_files

            # --- Data sheet generation (v5a) ---
            datasheet_path: Optional[str] = None
            try:
                datasheet_out = os.path.join(job.out_dir, "DATASHEET.md")
                input_dir = os.path.dirname(os.path.abspath(job.input_file))
                existing_ds_candidate = os.path.join(input_dir, "DATASHEET.md")
                existing_ds = existing_ds_candidate if os.path.isfile(
                    existing_ds_candidate) else None
                datasheet_path = generate_datasheet(
                    ir=ir,
                    intent_result=intent_result,
                    req_result=req_result,
                    out_path=datasheet_out,
                    existing_path=existing_ds,
                )
                output_files.append(datasheet_path)
                if job.verbose:
                    print(f"[pssgen] Data sheet written: {datasheet_path}")
            except Exception as e:
                print(f"[pssgen] WARNING: datasheet generation failed: {e}")

            base_result = OrchestratorResult(
                success=True,
                output_files=output_files,
                attempts=attempt,
                gap_report_path=gap_report_path,
                datasheet_path=datasheet_path,
            )
            # --- Coverage closure loop (v3c-b) ---
            if job.coverage_loop is not None and job.coverage_loop > 0:
                return _run_closure_loop(
                    job=job,
                    ir=ir,
                    gap_report=gap_report if (intent_result is not None or req_result is not None) else None,
                    gap_report_path=gap_report_path,
                    intent_result=intent_result,
                    base_result=base_result,
                )
            return base_result

        last_fail_reason = result.reason
        if job.verbose:
            print(f"[orchestrator] Checker tier {result.tier} fail: {result.reason}")

    return OrchestratorResult(
        success=False,
        attempts=job.max_retries,
        last_fail_reason=last_fail_reason or "unknown",
    )
