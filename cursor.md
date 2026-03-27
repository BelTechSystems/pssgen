# Cursor Guidance for pssgen

This file tells Cursor what pssgen is, how it is architected, and the rules
that must not be broken during development. Read this before writing any code.
When in doubt about a design decision, the answer is in DESIGN.md or SDS.md.

---

## What This Tool Does

pssgen is an AI-driven CLI tool that accepts an HDL source file or plain English
verification intent and produces:
- A PSS (Portable Stimulus Standard) model as the portable intermediate representation
- A UVM 1.2 SystemVerilog testbench (targeting Vivado/XSIM or Questa)
- C/C++ test cases for embedded or post-silicon validation

It is open source, simulator-agnostic, and requires no EDA tool license to run
in basic mode.

---

## Current Build Phase

**v0 — Walking Skeleton**

The only goal right now is: `counter.v` goes in, 7 files come out, `xvlog` compiles
them clean. Do not add features beyond v0 scope until this is done and all v0 tests
pass. See README.md for the full phase roadmap.

---

## Architecture: The Five Layers

Every piece of code lives in exactly one of these layers. If you are unsure where
something belongs, ask before placing it.

```
Layer 1  parser/          HDL source → IR. No UVM knowledge here.
Layer 2  ir.py            The IR dataclass. Vendor-neutral. Append-only.
Layer 3  agents/          LLM + template rendering. Reads IR. Writes artifacts.
Layer 4  checkers/        Validates agent output. Returns pass/fail + reason.
Layer 5  emitters/        IR + artifacts → simulator-specific files. Only layer
                          allowed to contain simulator-specific knowledge.
```

`orchestrator.py` sits above all layers. It coordinates the loop. It does not
contain UVM or PSS knowledge.

`cli.py` is the entry point only. It parses arguments and calls the orchestrator.
No business logic in cli.py.

---

## The Rules (Do Not Break These)

### Rule 1: The orchestrator owns the retry loop
Agents do not retry themselves. The orchestrator calls the agent, passes the result
to the checker, and retries with the checker's failure reason injected as context
if the checker fails. Max retries is configurable (default 3).

```python
# CORRECT — orchestrator controls the loop
for attempt in range(max_retries):
    artifacts = agent.generate(ir, fail_reason=last_fail_reason)
    result = checker.check(artifacts)
    if result.passed:
        break
    last_fail_reason = result.reason

# WRONG — agent retrying internally
def generate(ir):
    for attempt in range(3):   # NO. Don't do this.
        ...
```

### Rule 2: The IR is append-only
Never rename, remove, or change the type of an existing IR field. New fields are
added as Optional with a default of None. This preserves backward compatibility
across all phases.

```python
# CORRECT — adding a new field in v1
@dataclass
class IR:
    design_name: str
    hdl_source: str
    ports: list[Port]
    pss_intent: Optional[str] = None   # new in v1, optional

# WRONG — renaming an existing field
@dataclass
class IR:
    name: str              # was design_name — NEVER do this
```

### Rule 3: Templates constrain the LLM
The Jinja2 templates in templates/ provide the structural UVM/PSS skeleton.
The LLM fills dynamic content only (class names, port bindings, signal wire-ups).
Never ask the LLM to generate raw UVM from a blank prompt. Always render the
template first and let the LLM fill the placeholders.

### Rule 4: The emission layer is the only simulator-aware layer
No Vivado-specific or Questa-specific strings appear anywhere except emitters/.
If you find yourself writing "xvlog" or "vsim" outside of emitters/ or checkers/,
stop and refactor.

### Rule 5: Stubs exist from day one
All future-phase modules are stubbed with NotImplementedError from the start.
The directory tree and import paths are stable across all phases. Never restructure
the tree to add a new module — it should already be there as a stub.

### Rule 6: The checker contract is frozen
The checker's external interface never changes:
```python
def check(artifacts: list[Artifact], sim_target: str) -> CheckResult:
    ...
# CheckResult: passed: bool, tier: int, reason: str
```
Internal checks grow over time. The interface does not change.

---

## Component Interfaces (Stable Contracts)

```python
# orchestrator.py
def run(job: JobSpec) -> OrchestratorResult:
    # JobSpec:          input_file, top_module, out_dir, sim_target, max_retries
    # OrchestratorResult: success, output_files, attempts, last_fail_reason

# parser/verilog.py
def parse(source_file: str, top_module: str | None) -> IR:
    # Raises ParseError on failure

# agents/structure_gen.py
def generate(ir: IR, fail_reason: str | None = None) -> list[Artifact]:
    # Artifact: filename (str), content (str)
    # fail_reason injected into LLM prompt on retry

# checkers/verifier.py
def check(artifacts: list[Artifact], sim_target: str) -> CheckResult:
    # CheckResult: passed (bool), tier (int 1-3), reason (str)

# emitters/vivado.py
def emit(ir: IR, artifacts: list[Artifact], out_dir: str) -> list[str]:
    # Returns list of written file paths
```

---

## The IR Dataclass (v0)

```python
@dataclass
class Port:
    name: str
    direction: str       # "input" | "output" | "inout"
    width: int
    role: str            # "clock" | "reset_n" | "reset" | "control" | "data"

@dataclass
class IR:
    design_name: str
    hdl_source: str
    hdl_language: str    # "verilog" | "systemverilog" | "vhdl"
    ports: list[Port]
    parameters: dict     # name → default_value
    emission_target: str # "vivado" | "questa" | "generic"
    output_dir: str
```

Do not add fields to the IR without checking the append-only rule above.

---

## Checker: Three Tiers

The checker runs tiers in order and stops at the first failure.

```
Tier 1 — Structural (no simulator needed, pure regex)
  - Each expected class declaration is present
  - uvm_component_utils or uvm_object_utils macro present per class
  - build_phase and run_phase present in driver and agent
  - write() task present in monitor
  - Interface correctly bound in agent

Tier 2 — Syntax (calls xvlog or vlog, checks exit code)
  - xvlog --sv --nolog *.sv   (Vivado)
  - vlog -quiet *.sv          (Questa)
  - Compiler stderr returned verbatim as fail reason

Tier 3 — Smoke
  - build.tcl or build script exists
  - All `include paths in generated files resolve
  - Required UVM base classes referenced correctly
```

---

## Test Requirements

Every function has a unit test. Every component interface has an integration test.
Every phase has an end-to-end test. The LLM is stubbed in unit and integration tests.
Only e2e tests call the real LLM.

Key v0 tests that must pass before any v1 work begins:

```
test_parse_verilog_counter       All 5 ports extracted, roles correct
test_ir_roundtrip                Serialize → deserialize → assert equal
test_check_tier1_pass            Valid files → CheckResult.passed == True
test_check_tier1_missing_phase   Missing run_phase → tier==1, reason contains 'run_phase'
test_orchestrator_retry          Injected checker fail → retry fires, reason in next prompt
test_e2e_counter_vivado          Full pipeline → xvlog exit code 0
```

Run tests before every commit:
```bash
pytest tests/ -v --tb=short
```

---

## v0 Canonical Test Case

Input file: `tests/fixtures/counter.v`

```verilog
module up_down_counter #(parameter WIDTH = 8) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        enable,
    input  logic        up_down,
    output logic [7:0]  count
);
```

Expected IR after parsing:
```json
{
  "design_name": "up_down_counter",
  "hdl_source": "tests/fixtures/counter.v",
  "hdl_language": "verilog",
  "ports": [
    {"name": "clk",     "direction": "input",  "width": 1, "role": "clock"},
    {"name": "rst_n",   "direction": "input",  "width": 1, "role": "reset_n"},
    {"name": "enable",  "direction": "input",  "width": 1, "role": "control"},
    {"name": "up_down", "direction": "input",  "width": 1, "role": "control"},
    {"name": "count",   "direction": "output", "width": 8, "role": "data"}
  ],
  "parameters": {"WIDTH": "8"},
  "emission_target": "vivado",
  "output_dir": "./out"
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

v0 definition of done: `xvlog --sv *.sv` exits 0.

---

## What Not To Do

- Do not add PSS generation logic until v0 e2e test passes cleanly.
- Do not implement the Questa emitter until v2 is scheduled.
- Do not put simulator-specific strings outside emitters/ or checkers/.
- Do not add new IR fields without confirming they are backward-compatible.
- Do not let agents contain retry logic.
- Do not use unicode bullet characters in generated output — use UVM proper syntax.
- Do not generate raw UVM from a blank LLM prompt — always use templates.

---

## Where Design Decisions Live

- **README.md** — what the tool does, CLI reference, roadmap, structure
- **DESIGN.md** — why the tool is designed this way (read before refactoring)
- **SDS.md** — full software design specification with component interfaces
- **cursor.md** — this file: rules, contracts, and Cursor-specific guidance

When Cursor suggests a refactor that conflicts with any rule in this file,
check DESIGN.md for the rationale before accepting the suggestion. The rules
exist for reasons that may not be obvious from the code alone.
