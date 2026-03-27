"""pssgen CLI entry point. Argument parsing only — no business logic here."""
import argparse
import sys
from orchestrator import run, JobSpec


def main():
    parser = argparse.ArgumentParser(
        prog="pssgen",
        description="AI-driven PSS + UVM + C testbench generator."
    )
    parser.add_argument("--input",  required=True, help="HDL source file or intent .txt")
    parser.add_argument("--top",    default=None,  help="Top-level module name")
    parser.add_argument("--out",    default="./out", help="Output directory (default: ./out)")
    parser.add_argument("--sim",    default="vivado", choices=["vivado", "questa", "generic"])
    parser.add_argument("--retry",  default=3, type=int, help="Max retry attempts (default: 3)")
    parser.add_argument("--dump-ir", action="store_true", help="Write IR snapshot to <out>/ir.json")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call; render templates only")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    job = JobSpec(
        input_file=args.input,
        top_module=args.top,
        out_dir=args.out,
        sim_target=args.sim,
        max_retries=args.retry,
        dump_ir=args.dump_ir,
        no_llm=args.no_llm,
        verbose=args.verbose,
    )
    result = run(job)
    if not result.success:
        print(f"[pssgen] FAILED after {result.attempts} attempt(s): {result.last_fail_reason}", file=sys.stderr)
        sys.exit(1)
    if args.verbose:
        print(f"[pssgen] Done in {result.attempts} attempt(s). Files: {result.output_files}")
    sys.exit(0)


if __name__ == "__main__":
    main()
