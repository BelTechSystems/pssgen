# pssgen

> Describe your verification intent in plain English.  
> Get a PSS model, working UVM testbench, and C test cases out.  
> Runs free with AMD Vivado/XSIM. Works with Siemens Questa. No license required.

---

## What pssgen Is

`pssgen` is an open-source, AI-driven command-line tool that bridges the gap between
verification intent and working testbench code. An engineer describes what a design
should do — in plain language or from an HDL source file — and pssgen produces:

- A **Portable Stimulus Standard (PSS) model** as the intermediate representation
- A **UVM 1.2-compliant SystemVerilog testbench** targeting Vivado/XSIM or Questa
- **C/C++ test cases** for embedded or post-silicon validation

PSS is the Accellera standard (current release: v3.0, August 2024) that defines
verification intent once and lets it execute across simulation, FPGA prototyping,
and post-silicon environments. pssgen makes PSS accessible without an enterprise
tool license.

---

## Why pssgen Exists

The UVM testbench generation space is occupied by well-funded startups and incumbent
EDA vendors (Siemens Questa Agentic Toolkit, MooresLabAI, ChipAgents). They generate
initial scaffolds well.

Two problems remain unsolved for the mid-market FPGA and ASIC engineer:

1. **The PSS onramp is broken.** PSS is the right abstraction for portable,
   reusable verification. The tooling that exists is enterprise-licensed and
   requires a significant mental model shift to adopt. No open, AI-assisted
   onramp exists.

2. **Coverage closure is manual.** Every tool generates the initial testbench.
   Nobody has built an open, iterative loop that simulates, measures coverage,
   identifies holes, regenerates targeted sequences, and drives to closure
   automatically.

pssgen addresses both, with PSS as the portable IR that makes the solution
simulator-agnostic by design.

---

## Architecture Overview

```
plain English intent / HDL source file
            │
            ▼
    ┌───────────────┐
    │  HDL Parser   │  Port extraction, role classification
    └───────────────┘
            │
            ▼
    ┌───────────────┐
    │      IR       │  Vendor-neutral intermediate representation
    └───────────────┘
            │
            ▼
    ┌───────────────────────────────────────┐
    │            Orchestrator               │
    │   (retry loop, max attempts, context  │
    │    injection on checker fail)         │
    └───────────────────────────────────────┘
            │
            ▼
    ┌───────────────┐     ┌─────────────────────┐
    │  PSS Agent    │────▶│   Checker           │
    │  (LLM +       │◀────│   Tier 1: structure  │
    │   templates)  │fail │   Tier 2: syntax     │
    └───────────────┘     │   Tier 3: smoke      │
            │pass         └─────────────────────┘
            ▼
    ┌────────────────────────────────────────┐
    │          Emission Layer                │
    │  Vivado/XSIM  │  Questa  │  Generic C  │
    └────────────────────────────────────────┘
            │
            ▼
    ./out/  PSS model + UVM .sv files + C tests + build script
```

**Key design principles:**

- The orchestrator owns the retry loop. Agents do not retry themselves.
- The IR is append-only. Fields are added across phases; existing fields are never
  renamed or removed.
- Templates constrain the LLM. Structural UVM/PSS skeletons come from Jinja2
  templates. The LLM fills dynamic, design-specific content only.
- The checker's external contract is stable. Internal checks grow over time
  without changing the orchestrator interface.
- The emission layer is the only component with simulator-specific knowledge.
  Adding a new simulator target requires one new emitter only.

---

## CLI Reference

```
pssgen --input  <file>      HDL source (.v, .sv, .vhd) or intent description (.txt)
        --top   <module>    Top-level module name (required if multiple modules)
        --out   <dir>       Output directory (default: ./out)
        --sim   <target>    Emission target: vivado | questa | generic (default: vivado)
        --retry <n>         Max orchestrator retry attempts (default: 3)
        --dump-ir           Write IR snapshot to <out>/ir.json
        --verbose           Print orchestrator loop steps to stdout
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Success — all artifacts generated and verified |
| 1 | Checker failure — retries exhausted |
| 2 | Parse failure — HDL source could not be parsed |
| 3 | Configuration error — invalid arguments |

---

## Phased Development Roadmap

pssgen is built using a **vertical slice / walking skeleton** methodology.
Each phase delivers a working end-to-end system. No phase breaks the previous
phase's test suite. Capabilities are widened only after the current phase is
verified end-to-end.

### v0 — Walking Skeleton *(current)*
**Goal:** Prove the full pipeline with the simplest meaningful design.

- Input: `counter.v` (8-bit up/down counter, hardcoded)
- Output: UVM 1.2 scaffold (interface, driver, monitor, sequencer, agent, test) + `build.tcl`
- Emission target: Vivado/XSIM only
- Definition of done: `xvlog --sv *.sv` exits 0 (compiles clean)
- Orchestrator retry loop fires at least once in automated testing

### v1 — Natural Language Intent + PSS Model
**Goal:** Accept plain English verification intent; produce a PSS model as IR.

- Input: natural language description of verification intent (`.txt`)
- New agent: PSS model generator
- PSS model elaborates in the Accellera open PSS reference tool
- VHDL and SystemVerilog parser stubs promoted to working implementations

### v2 — PSS → UVM + C Output
**Goal:** One PSS model produces two output targets.

- Emission: UVM 1.2 SystemVerilog (existing) + C/C++ test cases (new)
- Questa emission target stub promoted to working implementation
- Both targets compile clean from the same PSS model

### v3 — Coverage Closure Feedback Loop
**Goal:** Iterative simulation-driven coverage closure.

- Reads coverage database (Vivado XML or Questa UCDB) after each sim run
- Identifies uncovered bins; feeds gap analysis to sequence generator
- Coverage holes measurably reduce on second orchestrator pass

### v4 — Register / RAL Intent via PSS
**Goal:** Highest daily-use value for FPGA engineers.

- Plain English register intent → PSS register model → UVM RAL model
- CSR programming sequences generated automatically
- SVA assertions generated from register access rules

---

## Project Structure

```
pssgen/
├── README.md                   ← this file
├── DESIGN.md                   ← architecture decisions and design rationale
├── cursor.md                   ← Cursor AI coding assistant guidance
├── SDS.md                      ← Software Design Specification (full)
├── cli.py                      ← argparse entry point
├── orchestrator.py             ← job loop, retry logic, checker calls
├── ir.py                       ← IR dataclass, JSON serialize/deserialize
├── parser/
│   ├── __init__.py
│   ├── verilog.py              ← regex-based port extractor (v0)
│   ├── systemverilog.py        ← stub → v1
│   └── vhdl.py                 ← stub → v1
├── agents/
│   ├── __init__.py
│   ├── structure_gen.py        ← UVM scaffold agent (v0)
│   └── pss_gen.py              ← PSS model agent → v1
├── checkers/
│   ├── __init__.py
│   └── verifier.py             ← 3-tier checker
├── emitters/
│   ├── __init__.py
│   ├── vivado.py               ← .sv files + build.tcl (v0)
│   ├── questa.py               ← stub → v2
│   └── generic_c.py            ← stub → v2
├── templates/
│   ├── uvm/
│   │   ├── interface.sv.jinja
│   │   ├── driver.sv.jinja
│   │   ├── monitor.sv.jinja
│   │   ├── sequencer.sv.jinja
│   │   ├── agent.sv.jinja
│   │   ├── test.sv.jinja
│   │   └── build_vivado.tcl.jinja
│   └── pss/
│       └── component.pss.jinja ← v1
└── tests/
    ├── fixtures/
    │   ├── counter.v           ← canonical v0 test input
    │   └── counter_intent.txt  ← canonical v1 test input
    ├── test_parser.py
    ├── test_ir.py
    ├── check.py
    ├── test_orchestrator.py
    └── test_e2e.py             ← end-to-end: counter.v → xvlog compiles clean
```

---

## Stub Convention

All future-phase modules exist in the tree from day one with a `NotImplementedError`.
This keeps import paths stable and prevents structural refactoring later.

```python
# questa.py
def emit(ir, out_dir):
    raise NotImplementedError(
        "Questa emission target not yet implemented. "
        "Use --sim vivado. Tracked in roadmap v2.")
```

---

## Dependencies

**Runtime:**
- Python >= 3.11
- `jinja2` — template rendering
- `anthropic` — LLM API (Claude)

**Development:**
- `pytest` — test runner
- `pytest-cov` — coverage reporting

**Optional (for checker tier 2):**
- AMD Vivado (free) — `xvlog` for SystemVerilog syntax check
- Siemens Questa — `vlog` for syntax check

No EDA tool license is required to run pssgen in tier-1-only mode.

---

## Installation

```bash
git clone https://github.com/<your-org>/pssgen.git
cd pssgen
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=your_key_here
```

## Quickstart

```bash
# Generate a UVM testbench for an up/down counter (v0)
pssgen --input tests/fixtures/counter.v --top up_down_counter --sim vivado

# Inspect the IR snapshot
pssgen --input tests/fixtures/counter.v --dump-ir --verbose
```

---

## Contributing

pssgen is open source (MIT license). Contributions welcome — particularly:
- HDL parser improvements (VHDL, SystemVerilog edge cases)
- Additional Jinja2 UVM templates
- PSS model generation prompt improvements
- Coverage database readers (Vivado XML, Questa UCDB)

Please read `DESIGN.md` before contributing. The architectural decisions recorded
there explain *why* the code is structured as it is, not just *what* it does.
Understanding the design rationale prevents well-intentioned changes that violate
core principles (IR append-only policy, orchestrator owns retry logic, etc.).

---

## License

MIT License. See `LICENSE` for details.

---

## Status

**Current phase: v0 — Walking Skeleton**  
The pipeline is real. The counter goes in. The UVM scaffold comes out. It compiles.
Everything after that is additive.
