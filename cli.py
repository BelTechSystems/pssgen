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
#     Parse CLI arguments, build JobSpec, invoke orchestrator, exit 0/1/3.
#
# DEPENDENCIES:
#   Standard library:  argparse, sys
#   Internal:          orchestrator, parser.dispatch
#
# HISTORY:
#   v0    2026-03-27  SB  Initial implementation; core HDL-to-UVM arguments
#   v2a   2026-03-27  SB  Added --intent flag for structured natural language intent
#   v3a   2026-03-28  SB  Added --req, --no-intent, --no-req, --scaffold, --coverage-loop
#   v3b   2026-03-28  SB  Print gap report path from orchestrator result
#
# ===========================================================
"""cli.py — Command-line entry point for pssgen.

Phase: v0
Layer: Entry point (above orchestration layers)

Parses command-line arguments and dispatches one orchestrator run.
"""
import argparse
import sys
from orchestrator import run, JobSpec
from parser.dispatch import resolve_parser


def main() -> None:
    """Run the pssgen CLI entry point.

    Parses command-line arguments, builds a `JobSpec`, and invokes the
    orchestrator. Exits with status code 0 on success and 1 on failure.

    The optional ``--intent`` flag allows engineers to provide structured
    natural language verification intent that supplements HDL-derived IR.
    """
    parser = argparse.ArgumentParser(
        prog="pssgen",
        description="AI-driven PSS + UVM + C testbench generator."
    )
    parser.add_argument("--input",  required=True, help="HDL source file (.v, .sv, .vhd, .vhdl)")
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
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        resolve_parser(args.input)
    except ValueError as exc:
        print(f"[pssgen] CONFIG ERROR: {exc}", file=sys.stderr)
        sys.exit(3)

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
