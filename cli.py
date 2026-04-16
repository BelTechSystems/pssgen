# ===========================================================
# FILE:         cli.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Entry point for the pssgen command-line interface. Parses arguments,
#   constructs a JobSpec, and invokes the orchestrator. All business logic
#   is delegated; this module is argument parsing and dispatch only.
#
# LAYER:        Entry point (above all pipeline layers)
# PHASE:        v0
#
# FUNCTIONS:
#   main()
#     Parse CLI arguments, load pssgen.toml config, build JobSpec,
#     invoke orchestrator, exit 0/1/3.
#
# DEPENDENCIES:
#   Standard library:  argparse, os, sys
#   Internal:          config, orchestrator, parser.dispatch
#
# HISTORY:
#   v0    2026-03-27  SB  Initial implementation; core HDL-to-UVM arguments
#   v2a   2026-03-27  SB  Added --intent flag for structured natural language intent
#   v3a   2026-03-28  SB  Added --req, --no-intent, --no-req, --scaffold, --coverage-loop
#   v3b   2026-03-28  SB  Print gap report path from orchestrator result
#   v3c-a 2026-03-29  SB  pssgen.toml config auto-detection, --config flag,
#                          --coverage-db flag, file resolution verbose reporting
#   v4a   2026-04-03  SB  Added --reg-map flag; verbose reg-map resolution reporting
#   v5a   2026-04-07  SB  import-reqs subcommand for .docx requirement extraction
#   v6c   2026-04-16  SB  Added --collect-results and --sim-log flags (OI-29)
#
# ===========================================================
"""cli.py — Command-line entry point for pssgen.

Phase: v0
Layer: Entry point (above orchestration layers)

Parses command-line arguments, loads pssgen.toml project config, merges
config with CLI flags (CLI takes priority), and dispatches one orchestrator
run.
"""
import argparse
import os
import sys

from config import find_project_config, load_project_config, merge_config_with_args
from orchestrator import run, JobSpec
from parser.dispatch import resolve_parser
from parser.context import resolve_regmap_file


def _dispatch_import_reqs() -> None:
    """Handle the ``import-reqs`` subcommand and exit.

    Parses import-reqs-specific arguments from sys.argv, dispatches to
    the command handler, and calls sys.exit with the return code.
    """
    from commands.import_reqs import run_import_reqs

    sub_parser = argparse.ArgumentParser(
        prog="pssgen import-reqs",
        description=(
            "Extract requirements from a source document and write a .req bootstrap file.\n"
            "The .req file is never overwritten once it exists."
        ),
    )
    sub_parser.add_argument(
        "--from",
        dest="from_format",
        required=True,
        metavar="FORMAT",
        help="Source format. Currently only 'word' (.docx) is supported.",
    )
    sub_parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help="Path to the source document. If omitted, reads from pssgen.toml [requirements] source.",
    )
    sub_parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Explicit output .req file path. Defaults to <design_name>.req in the project directory.",
    )
    sub_args = sub_parser.parse_args(sys.argv[2:])
    sys.exit(run_import_reqs(sub_args))


def _companion_path(input_file: str, ext: str) -> str | None:
    """Return ``<stem><ext>`` if that file exists alongside *input_file*.

    Args:
        input_file: Path to the HDL input file.
        ext: File extension including leading dot, e.g. ``".intent"``.

    Returns:
        Absolute path to the companion file if it exists, else None.
    """
    stem = os.path.splitext(os.path.abspath(input_file))[0]
    path = stem + ext
    return path if os.path.isfile(path) else None


def main() -> None:
    """Run the pssgen CLI entry point.

    Parses command-line arguments, loads pssgen.toml project configuration
    (auto-detected or via --config), merges config with CLI flags (CLI
    takes priority), builds a ``JobSpec``, and invokes the orchestrator.
    Exits with status code 0 on success, 1 on failure, and 3 on bad input.
    """
    # ------------------------------------------------------------------
    # Subcommand dispatch: check for known subcommands before the main
    # argument parser runs, so they don't collide with pipeline flags.
    # ------------------------------------------------------------------
    if len(sys.argv) > 1 and sys.argv[1] == "import-reqs":
        _dispatch_import_reqs()
        return  # unreachable — _dispatch_import_reqs calls sys.exit

    # ------------------------------------------------------------------
    # Preliminary parse: discover --input and --config before full parse
    # so we can locate pssgen.toml relative to the input file's directory.
    # ------------------------------------------------------------------
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--input", default=None)
    pre_parser.add_argument("--config", default=None)
    pre_args, _ = pre_parser.parse_known_args()

    # Locate pssgen.toml: explicit --config wins, then search from input
    # file directory, then fall back to cwd.
    config_path: str | None = None
    config_source: str = "none"

    if pre_args.config:
        config_path = os.path.abspath(pre_args.config)
        config_source = "explicit"
    elif pre_args.input:
        start_dir = os.path.dirname(os.path.abspath(pre_args.input))
        config_path = find_project_config(start_dir)
        if config_path:
            config_source = "auto-detected"
    else:
        config_path = find_project_config()
        if config_path:
            config_source = "auto-detected"

    loaded_config: dict = {}
    if config_path:
        loaded_config = load_project_config(config_path)

    # ------------------------------------------------------------------
    # Full argument parser
    # ------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        prog="pssgen",
        description="AI-driven PSS + UVM + C testbench generator."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="HDL source file (.v, .sv, .vhd, .vhdl)",
    )
    parser.add_argument(
        "--config",
        default=None,
        metavar="FILE",
        help="Project config file (default: pssgen.toml, auto-detected from input directory).",
    )
    parser.add_argument(
        "--intent",
        default=None,
        help=(
            "Structured natural language intent file (.intent). "
            "Supplements HDL port inference with engineer-provided verification intent."
        ),
    )
    parser.add_argument("--top",    default=None,  help="Top-level module name")
    parser.add_argument("--out",    default="./out", help="Output directory (default: ./out)")
    parser.add_argument("--sim",    default="vivado", choices=["vivado", "questa", "generic"])
    parser.add_argument("--retry",  default=3, type=int, help="Max retry attempts (default: 3)")
    parser.add_argument("--dump-ir", action="store_true", help="Write IR snapshot to <out>/ir.json")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help=(
            "Skip LLM call; render templates only. "
            "Used for testing and CI. Never requires ANTHROPIC_API_KEY."
        ),
    )
    parser.add_argument(
        "--req",
        default=None,
        help="Requirements file (.req). Supplements intent with formal requirement IDs.",
    )
    parser.add_argument(
        "--no-intent",
        action="store_true",
        help="Suppress auto-loading of <stem>.intent alongside the input file.",
    )
    parser.add_argument(
        "--no-req",
        action="store_true",
        help="Suppress auto-loading of <stem>.req alongside the input file.",
    )
    parser.add_argument(
        "--scaffold",
        action="store_true",
        help=(
            "Generate _generated.intent and _generated.req scaffold files in out_dir. "
            "Existing scaffolds are never overwritten."
        ),
    )
    parser.add_argument(
        "--coverage-loop",
        default=None,
        type=int,
        metavar="N",
        help="(Stub — not yet implemented; see v3c) Coverage closure loop iterations.",
    )
    parser.add_argument(
        "--coverage-db",
        default=None,
        metavar="PATH",
        help="(Stub — not yet implemented; see v3c) Coverage database path.",
    )
    parser.add_argument(
        "--reg-map",
        default=None,
        dest="reg_map",
        metavar="FILE",
        help=(
            "Register map spreadsheet (.xlsx) or intent file (.intent) containing "
            "a register map: section. Auto-detected as <stem>_regmap.xlsx alongside "
            "the input file if not specified."
        ),
    )
    parser.add_argument(
        "--collect-results",
        action="store_true",
        dest="collect_results",
        help=(
            "Parse sim log and write RTL results back to the VPR spreadsheet. "
            "Requires --sim-log."
        ),
    )
    parser.add_argument(
        "--sim-log",
        default=None,
        dest="sim_log",
        metavar="PATH",
        help="Path to xsim.log; required with --collect-results.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Validate --collect-results dependency
    # ------------------------------------------------------------------
    if args.collect_results and not args.sim_log:
        print(
            "[pssgen] ERROR: --collect-results requires --sim-log <path>",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Merge pssgen.toml config into args (CLI flags take priority)
    # ------------------------------------------------------------------
    if loaded_config:
        intent_before_merge = args.intent
        req_before_merge = args.req
        merge_config_with_args(loaded_config, args)
        intent_from_cli = intent_before_merge is not None
        req_from_cli = req_before_merge is not None
    else:
        intent_from_cli = args.intent is not None
        req_from_cli = args.req is not None

    # ------------------------------------------------------------------
    # Validate that input_file is now set (CLI or config)
    # ------------------------------------------------------------------
    if not args.input:
        parser.error(
            "--input is required (provide on command line or set [input] file in pssgen.toml)"
        )

    # ------------------------------------------------------------------
    # Validate HDL extension before further processing
    # ------------------------------------------------------------------
    try:
        resolve_parser(args.input)
    except ValueError as exc:
        print(f"[pssgen] CONFIG ERROR: {exc}", file=sys.stderr)
        sys.exit(3)

    # ------------------------------------------------------------------
    # File resolution verbose reporting (D-013)
    # ------------------------------------------------------------------
    if args.verbose:
        # Config
        if config_path:
            print(f"[pssgen] Config:  {config_path} ({config_source})")
        else:
            print("[pssgen] Config:  none")

        # Input
        print(f"[pssgen] Input:   {os.path.abspath(args.input)}")

        # Intent
        if intent_from_cli:
            intent_label = f"{args.intent} (explicit)"
        elif args.intent is not None:
            # Value came from TOML merge
            intent_label = f"{args.intent} (from pssgen.toml)"
        else:
            auto_intent = _companion_path(args.input, ".intent")
            if auto_intent and not args.no_intent:
                intent_label = f"{auto_intent} (auto-detected)"
            else:
                intent_label = "none — create <stem>.intent or use --intent <file> for richer PSS output"
        print(f"[pssgen] Intent:  {intent_label}")

        # Req
        if req_from_cli:
            req_label = f"{args.req} (explicit)"
        elif args.req is not None:
            req_label = f"{args.req} (from pssgen.toml)"
        else:
            auto_req = _companion_path(args.input, ".req")
            if auto_req and not args.no_req:
                req_label = f"{auto_req} (auto-detected)"
            else:
                req_label = "none — create <stem>.req or use --req <file> for requirements traceability"
        print(f"[pssgen] Req:     {req_label}")

        # Reg map
        resolved_regmap = resolve_regmap_file(args.input, args.reg_map)
        if args.reg_map:
            regmap_label = f"{resolved_regmap} (explicit)" if resolved_regmap else f"{args.reg_map} (not found)"
        elif resolved_regmap:
            regmap_label = f"{resolved_regmap} (auto-detected)"
        else:
            regmap_label = "none"
        print(f"[pssgen] Reg map: {regmap_label}")

    else:
        # Non-verbose: hint if no intent will be found
        if args.intent is None and not args.no_intent:
            auto_intent = _companion_path(args.input, ".intent")
            if not auto_intent:
                stem = os.path.splitext(os.path.basename(args.input))[0]
                print(
                    f"[pssgen] No intent file found. Using IR-only inference.\n"
                    f"         Create {stem}.intent or use --intent <file>\n"
                    f"         for richer PSS output."
                )

    # ------------------------------------------------------------------
    # Build JobSpec and run
    # ------------------------------------------------------------------
    job = JobSpec(
        input_file=args.input,
        intent_file=args.intent,
        top_module=args.top,
        out_dir=args.out,
        sim_target=args.sim,
        max_retries=args.retry,
        dump_ir=args.dump_ir,
        no_llm=args.no_llm,
        verbose=args.verbose,
        req_file=args.req,
        no_intent=args.no_intent,
        no_req=args.no_req,
        scaffold=args.scaffold,
        coverage_loop=args.coverage_loop,
        coverage_db=args.coverage_db,
        reg_map_file=args.reg_map,
        register_maps_list=loaded_config.get("register_maps_list"),
        collect_results=args.collect_results,
        sim_log=args.sim_log,
    )
    result = run(job)
    if not result.success:
        print(f"[pssgen] FAILED after {result.attempts} attempt(s): {result.last_fail_reason}", file=sys.stderr)
        sys.exit(1)
    if result.gap_report_path:
        print(f"[pssgen] Gap report written: {result.gap_report_path}")
    if args.verbose:
        print(f"[pssgen] Done in {result.attempts} attempt(s). Files: {result.output_files}")
    sys.exit(0)


if __name__ == "__main__":
    main()
