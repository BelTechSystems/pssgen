# pssgen — Claude Code Project Guidance

This file is read by Claude Code at the start of every session.
It contains the intent, constraints, and non-negotiable rules for pssgen.
Read DESIGN.md for the *why* behind each decision before making any significant change.

---

## What This Project Is and Why It Exists

pssgen is an open-source AI-driven CLI tool that converts HDL source files or
plain English verification intent into:
- A PSS (Portable Stimulus Standard v3.0) model as the portable IR
- A UVM 1.2 SystemVerilog testbench (Vivado/XSIM or Questa)
- C/C++ test cases for embedded or post-silicon validation

**Why PSS as the IR:** PSS is the Accellera standard that defines verification
intent once and executes it across simulation, FPGA prototyping, and post-silicon.
It is the right abstraction but has no open, AI-assisted onramp. pssgen is that
onramp. This positioning makes pssgen *complementary* to enterprise tools
(Siemens Questa, Cadence Perspec) rather than competing with them.

**Why open source MIT:** A solo developer cannot compete on engineering resources
with funded startups and incumbent EDA vendors. The competitive advantage is domain
expertise expressed in the design decisions, templates, and checker checks.
Open source with MIT license maximizes long-term adoption and community effect.

**Success criterion for v0:** `xvlog --sv *.sv` exits 0 on the generated counter
testbench. Everything after that is additive to a working system.

---

## Current Phase: v0 — Walking Skeleton

Do not add features beyond v0 scope until the v0 e2e test passes and all
v0 tests are green. The v0 scope is exactly:

- Input: `tests/fixtures/counter.v` (8-bit up/down counter)
- Output: 7 files in `./out/` (interface, driver, monitor, seqr, agent, test, build.tcl)
- Emission target: Vivado/XSIM only
- Gate: `xvlog --sv *.sv` exits 0

Phases v1 through v4 are defined in README.md. Do not implement them early.

---

## Architecture: Five Layers — One Responsibility Each

```
parser/       Layer 1  HDL source → IR. No UVM or PSS knowledge here.
ir.py         Layer 2  Vendor-neutral data model. Append-only.
agents/       Layer 3  LLM + Jinja2 templates → artifacts. Reads IR only.
checkers/     Layer 4  Validates artifacts. Returns CheckResult. No generation here.
emitters/     Layer 5  IR + artifacts → simulator-specific files. Only layer
                       allowed to contain simulator-specific strings.
```

`orchestrator.py` sits above all layers — it coordinates the loop.
`cli.py` is the entry point only — argument parsing, nothing else.

If a proposed change puts simulator-specific code outside `emitters/` or `checkers/`,
or puts retry logic inside an agent, stop and check DESIGN.md.

---

## The Six Rules That Must Not Break

### Rule 1: Orchestrator owns the retry loop
Agents are stateless. They accept `(ir, fail_reason)` and return artifacts.
The orchestrator calls the agent, passes artifacts to the checker, and retries
with the checker's failure reason injected into the next generation prompt.
Never put retry logic inside an agent.

### Rule 2: IR is append-only
Never rename, remove, or change the type of an existing IR field.
New fields are `Optional` with `None` default. This preserves backward
compatibility across all development phases.

```python
# CORRECT — new optional field
pss_intent: Optional[str] = None   # added in v1

# WRONG — renaming breaks v0 components
name: str   # was design_name — never do this
```

### Rule 3: Templates constrain the LLM
Jinja2 templates in `templates/` provide the structural UVM/PSS skeleton.
The LLM fills dynamic content only: class names, port wire-ups, signal bindings.
Never call the LLM with a blank prompt asking for raw UVM. Always render the
template first and pass it to the LLM for completion.

### Rule 4: Emission layer is the only simulator-aware layer
Strings like `xvlog`, `vsim`, `vlog`, Tcl script structure, UCDB paths belong
only in `emitters/` and `checkers/`. If you find yourself writing simulator-specific
strings anywhere else, refactor before committing.

### Rule 5: Stubs exist from day one, import paths never move
All future-phase modules (`pss_gen.py`, `questa.py`, `vhdl.py`, etc.) already
exist as stubs raising `NotImplementedError`. Their import paths are stable.
Never restructure the directory tree to add a new module.

### Rule 6: checker external contract is frozen
```python
def check(artifacts: list[Artifact], sim_target: str) -> CheckResult:
# CheckResult: passed: bool, tier: int, reason: str
```
Internal checks grow. This interface does not change.

---

## Component Contracts (Stable Across All Phases)

```python
# cli.py — entry point only, no business logic
def main() -> None

# orchestrator.py
def run(job: JobSpec) -> OrchestratorResult
# JobSpec: input_file, top_module, out_dir, sim_target, max_retries, dump_ir, verbose
# OrchestratorResult: success, output_files, attempts, last_fail_reason

# parser/verilog.py
def parse(source_file: str, top_module: str | None) -> IR
# Raises: ParseError

# agents/structure_gen.py
def generate(ir: IR, fail_reason: str | None = None) -> list[Artifact]
# Artifact: filename (str), content (str)

# checkers/verifier.py
def check(artifacts: list[Artifact], sim_target: str) -> CheckResult
# CheckResult: passed (bool), tier (int 1–3), reason (str)

# emitters/vivado.py
def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]
# Returns: list of written file paths
```

---

## IR Schema (v0 — Append-Only)

```python
@dataclass
class Port:
    name: str
    direction: str    # "input" | "output" | "inout"
    width: int
    role: str         # "clock" | "reset_n" | "reset" | "control" | "data"

@dataclass
class IR:
    design_name: str
    hdl_source: str
    hdl_language: str   # "verilog" | "systemverilog" | "vhdl"
    ports: list[Port]
    parameters: dict
    emission_target: str
    output_dir: str
    pss_intent: Optional[str] = None   # v1+
```

---

## checker: Three Tiers

Run in order. Stop and return on first failure.

```
Tier 1 — Structural (no simulator needed)
  Each expected class present; uvm_component_utils macro present;
  build_phase + run_phase in driver and agent; write() in monitor;
  build script exists.

Tier 2 — Syntax (calls xvlog or vlog, checks exit code)
  Compiler stderr returned verbatim as fail reason if non-zero exit.
  Skipped gracefully if simulator not installed.

Tier 3 — Smoke
  Build script exists; include paths resolve.
```

---

## Testing Standards

- Every function has a unit test
- Every component interface has an integration test
- Every phase has an end-to-end test
- LLM is mocked in unit and integration tests — only e2e calls the real API
- Run `pytest tests/ -v --tb=short` before every commit

**v0 tests that must all pass before v1 begins:**
```
test_parse_verilog_counter       5 ports, correct roles and widths
test_ir_roundtrip                serialize → deserialize → assert equal
test_check_tier1_pass            valid files → CheckResult.passed == True
test_check_tier1_missing_phase   missing run_phase → tier 1 fail, reason contains it
test_orchestrator_retry          injected fail → retry fires, reason in next prompt
test_e2e_counter_vivado          full pipeline → xvlog exit 0
```

---

## v0 Canonical Test Case

Input: `tests/fixtures/counter.v`

```verilog
module up_down_counter #(parameter WIDTH = 8) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        enable,
    input  logic        up_down,
    output logic [7:0]  count
);
```

Expected IR:
```json
{
  "design_name": "up_down_counter",
  "hdl_language": "verilog",
  "ports": [
    {"name": "clk",     "direction": "input",  "width": 1, "role": "clock"},
    {"name": "rst_n",   "direction": "input",  "width": 1, "role": "reset_n"},
    {"name": "enable",  "direction": "input",  "width": 1, "role": "control"},
    {"name": "up_down", "direction": "input",  "width": 1, "role": "control"},
    {"name": "count",   "direction": "output", "width": 8, "role": "data"}
  ]
}
```

Expected output files in `./out/`:
```
up_down_counter_if.sv
up_down_counter_driver.sv
up_down_counter_monitor.sv
up_down_counter_seqr.sv
up_down_counter_agent.sv
up_down_counter_test.sv
build.tcl
```

---

## How to Work Effectively With Claude Code on This Project

**Prefer goal + context over commands.**
Instead of "implement the Questa emitter," say "implement the Questa emission
target in emitters/questa.py following the same interface as emitters/vivado.py.
It should emit .sv files and a vsim-compatible Makefile. We are in v2 scope."
The why and the constraint together produce better output than the command alone.

**Use /clear between distinct tasks.**
Each phase gate (v0 → v1, v1 → v2, etc.) is a natural session boundary.
Start a fresh session when moving to a new phase. Accumulated context from
a previous phase can introduce drift in architectural decisions.

**Ask Claude Code to check before accepting.**
After any significant generation, ask: "Does this change violate any of the
six rules in CLAUDE.md?" Claude Code can self-check against this file.

**Let Claude Code run the tests.**
`pytest tests/ -v --tb=short` is the standard check. Claude Code can run this
directly and iterate on failures without you manually reviewing each diff.

**For design decisions, use the chat session.**
Architecture questions, phase planning, strategic trade-offs — bring those to
the Claude chat session where this project was designed. Implementation and
debugging belong in Claude Code. The chat session is the design partner;
Claude Code is the implementation partner. DESIGN.md is the bridge.

---

## What Not To Do

- Do not implement PSS generation until all v0 tests pass
- Do not implement the Questa or C emitters until v2 is scheduled
- Do not put simulator-specific strings outside `emitters/` or `checks/`
- Do not add IR fields without confirming append-only compatibility
- Do not put retry logic inside an agent
- Do not call the LLM with a blank UVM generation prompt — use templates first
- Do not restructure the directory tree — all stub paths are already correct

---

## Where Design Decisions Live

| File | Contains |
|------|----------|
| `README.md` | What the tool does, CLI reference, roadmap, project structure |
| `DESIGN.md` | Why every major decision was made — read before refactoring |
| `CLAUDE.md` | This file: rules, contracts, session guidance for Claude Code |
| `SDS.md` | Full software design specification |
