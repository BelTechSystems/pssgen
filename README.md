# pssgen

> **Four steps from HDL to verified IP:**
> 1. Point pssgen at your RTL and register map.
> 2. Import requirements from your Word SRS or Excel source document.
> 3. Populate the VPR — assign coverage methods, test names, and verification status.
> 4. Run pssgen. Get a PSS model, UVM testbench, UVM RAL model, gap report, and closure scripts.
>
> Runs free with AMD Vivado/XSIM. Works with Siemens Questa and Icarus. No license required.

---

## What pssgen Does

`pssgen` is an open-source, AI-driven command-line tool for FPGA and ASIC verification engineers. It connects your existing design files to a requirement-traced verification record — without requiring you to write boilerplate UVM or maintain a separate register model by hand.

### Step 1 — Parse your HDL and register map

```bash
pssgen --input uart.vhd --reg-map uart_regmap.xlsx --no-llm
```

pssgen reads your ports and register map, classifies signal roles, and generates a UVM scaffold with a complete RAL model. No other files required.

### Step 2 — Import your requirements

Bootstrap a Verification Planning and Results (VPR) spreadsheet directly from your Word SRS or Excel requirements document:

```bash
pssgen import-reqs --from word docs/UART-RS-001.docx --out uart_vplan.xlsx
pssgen import-reqs --from xlsx requirements/uart_reqs.xlsx --out uart_vplan.xlsx
```

Or start from the VPR template manually:

```
docs/pssgen_vpr_template.xlsx  ←  copy, rename, populate
```

The VPR is your single authoritative verification record: requirements, coverage methods, test assignments, and status in one spreadsheet. It replaces separate `.intent` and `.req` files for new designs.

### Step 3 — Populate the VPR

Open the generated VPR and fill in:
- **Covered_By** — which coverage item satisfies each requirement
- **Test_Name** — the test or sequence that exercises it
- **Verification_Category** — Functional / Structural / Protocol_Compliance / etc.
- **RTL_Status** — PASS / FAIL / BLOCKED as simulation results arrive

Leave **UART-BR-004** blank to see a Direction A gap fire on the next run.

### Step 4 — Run pssgen with the VPR

```toml
# pssgen.toml
[input]
vplan = "uart_vplan.xlsx"
```

```bash
pssgen   # reads pssgen.toml, VPR, and HDL — generates everything
```

**Output in `./out/`:**
- PSS v3.0 model — portable, simulator-independent verification intent
- UVM 1.2 testbench — interface, driver, monitor, sequencer, agent, test
- UVM RAL model — one `uvm_reg_block` per block, register sequences, system assembly
- C test cases for post-silicon bringup
- Requirement-traced gap report — Direction A errors (req with no coverage), Direction B warnings (coverage with no req)
- Coverage closure script for your simulator

The register map and VPR travel with the IP. When your block moves to the next program, the next verification engineer inherits the RAL model, sequences, and traceability record — not just the RTL.

---

### Input Levels

| Level | What you provide | What you get |
|---|---|---|
| 1 | HDL only | UVM scaffold, inferred PSS model, C test cases |
| 2 | HDL + register map | + UVM RAL model, register sequences, system assembly |
| 3 | HDL + register map + VPR | + requirement-traced gap report, coverage closure scripts |

---

What pssgen is:
A PSS model generator and verification artifact bootstrapper. It reads what the engineer has and produces portable verification intent plus the simulator-specific artifacts to execute it on a chosen target.

What pssgen is not:
A verification engine, a UVM framework, a simulator integration layer, or a protocol VIP generator. It generates the scaffolding and the intent model. The simulator and the UVM library execute the result.

---

## Why pssgen Exists

I spent years as the IP library custodian for a major aerospace company. My job was to build and maintain a shared library of verified HDL that project teams could draw from instead of designing the same blocks from scratch.

It didn't work the way it was supposed to.

Every project team had to re-verify the IP in their own environment. Our testbenches were simulator-specific and tightly coupled to our infrastructure. A team couldn't take our verification along with our design. Projects would rather clone a block and own it than participate in the shared library.

I think the answer is portable verification intent. The [Accellera Portable Stimulus Standard](https://www.accellera.org/activities/working-groups/portable-stimulus) (PSS v3.0) lets you express what an IP block needs to be verified against — not as a simulator-specific testbench, but as an abstract, declarative model that generates tests for any target environment.

pssgen makes PSS accessible without an enterprise EDA license.

→ [Full founding post on LinkedIn](https://linkedin.com/in/stevebelton)

---

## Quickstart — Your First Generated Testbench

### Prerequisites

```bash
python --version          # requires >= 3.11
pip install -e ".[dev]"   # installs jinja2, anthropic, openpyxl, pytest
export ANTHROPIC_API_KEY=your_key_here

```
### Environment Setup

pssgen calls the Anthropic API to generate PSS models and UVM
artifacts. You need an API key before running the main pipeline.

Create a `.env` file in the project root:
ANTHROPIC_API_KEY=your-key-here

pssgen loads this file automatically at startup. You can also
export the key directly in your shell:
```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "your-key-here"

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=your-key-here

# Linux / macOS
export ANTHROPIC_API_KEY="your-key-here"
```

Get an API key at https://console.anthropic.com

**Note:** The `--no-llm` flag bypasses the API entirely and
renders templates only. This mode requires no API key and is
used for testing, CI, and verifying the pipeline structure
before committing to API calls.

### Try the canonical counter example

The repo includes a complete set of fixtures for an 8-bit up/down counter in `tests/fixtures/`:

```
tests/fixtures/
  counter.vhd               ← VHDL source (also counter.v for Verilog)
  counter.intent            ← plain English verification intent
  counter.req               ← requirements file with FUNC-REQ IDs
  counter_regmap.xlsx       ← register map (full 4-sheet format)
  counter_regmap_simple.xlsx← register map (simple 15-column format)
  pssgen.toml               ← project config — run pssgen with no flags
```

**Simplest run — HDL only, no API key needed:**

```bash
pssgen --input tests/fixtures/counter.vhd \
       --top up_down_counter \
       --out ./out \
       --sim vivado \
       --no-llm
```

Output in `./out/`:
```
up_down_counter_if.sv
up_down_counter_driver.sv
up_down_counter_monitor.sv
up_down_counter_seqr.sv
up_down_counter_agent.sv
up_down_counter_test.sv
up_down_counter.pss
build.tcl
```

**With intent file — richer PSS coverage goals:**

```bash
pssgen --input tests/fixtures/counter.vhd \
       --intent tests/fixtures/counter.intent \
       --top up_down_counter \
       --out ./out \
       --sim vivado \
       --no-llm
```

**With register map — adds UVM RAL model:**

```bash
pssgen --input tests/fixtures/counter.vhd \
       --reg-map tests/fixtures/counter_regmap_simple.xlsx \
       --top up_down_counter \
       --out ./out \
       --sim vivado \
       --no-llm
```

Additional output:
```
counter_reg_block.sv      ← uvm_reg_block with all registers
counter_reg_pkg.sv        ← package wrapper
counter_reg_seq.sv        ← hw_reset_seq, rw_seq, named action sequences
```

**With everything — full traceability and gap report:**

```bash
pssgen --input tests/fixtures/counter.vhd \
       --intent tests/fixtures/counter.intent \
       --req tests/fixtures/counter.req \
       --reg-map tests/fixtures/counter_regmap.xlsx \
       --top up_down_counter \
       --out ./out \
       --sim vivado \
       --no-llm \
       --verbose
```

Additional output:
```
up_down_counter_gap_report.txt  ← bidirectional traceability report
run_closure_pass_1.sh           ← simulation closure script
```

**Using pssgen.toml — run with one word:**

```bash
cd tests/fixtures
pssgen        # reads pssgen.toml, finds all files automatically
```

---

## Using Your Own Design

### Step 1 — Point pssgen at your HDL

```bash
pssgen --input path/to/your_design.vhd --sim vivado --no-llm
```

pssgen reads your ports, classifies their roles (clock, reset, control, data), and generates a basic UVM scaffold. No other files required.

### Step 2 — Add your register map (optional)

Take the spreadsheet your designer already maintains. If it has these 15 columns, pssgen reads it as-is — no reformatting required:

```
Block Name | Register Name | Register Offset | Register Width |
Register Description | Field Name | Bit Offset | Bit Width |
Access | Reset Value | Field Description | Volatile |
Hardware Access | Software Access | Field Enumerations
```

Three optional columns can be added at the right edge of your existing file:

```
base_address | req_id | pss_action
```

Pass it with `--reg-map` or drop it alongside your HDL as `<design_stem>_regmap.xlsx` and pssgen finds it automatically.

**Multi-block system — each designer keeps their own file:**

```toml
# pssgen.toml
[[register_maps]]
file         = "uart/uart_regmap.xlsx"
base_address = "0x4000_0000"

[[register_maps]]
file         = "gpio/gpio_regmap.xlsx"
base_address = "0x4001_0000"
```

pssgen generates one `_reg_block.sv` per block and a `<project>_reg_map.sv` system assembly.

### Step 3 — Add a plain English intent file (optional)

Create `your_design.intent` alongside your HDL. Write in plain English:

```
reset behavior:
  Apply rst_n low for at least 2 clock cycles before any
  counting sequence begins.

coverage goals:
  Count reaches maximum value and rolls over.
  Enable deasserted mid-sequence — count must hold.

corner cases:
  Reset during an active counting sequence.
```

Any section headings work. The AI maps your words to PSS constructs.

### Step 4 — Add requirements (optional)

Create `your_design.req` or tag entries in your intent file with requirement IDs:

```
coverage goals:
  Count reaches maximum value and rolls over. [FUNC-REQ-113]
  Enable deasserted mid-sequence. [FUNC-REQ-114]
```

pssgen detects your requirement ID scheme automatically — SYS-REQ, FUNC-REQ, IF-REQ, PERF-REQ, or any similar scheme. No configuration needed.

### Step 5 — Set up pssgen.toml for the team

```toml
# pssgen.toml — place at project root
[project]
name = "my_uart"

[input]
file   = "rtl/uart.vhd"
top    = "uart_top"
intent = "verification/uart.intent"
req    = "requirements/uart.req"

[output]
dir = "./out"
sim = "vivado"

[register_maps]
file         = "regmaps/uart_regmap.xlsx"
base_address = "0x4000_0000"
```

Then anyone on the team runs:

```bash
pssgen
```

---

## Project File Layout

### Simplest — all files co-located

```
my_project/
    uart.vhd
    uart.intent            ← auto-detected
    uart.req               ← auto-detected
    uart_regmap.xlsx       ← auto-detected as <stem>_regmap.xlsx
    pssgen.toml

pssgen
```

### Separated — RTL and verification separate

```
my_project/
    rtl/uart.vhd
    verification/uart.intent
    requirements/uart.req
    regmaps/uart_regmap.xlsx

pssgen --input rtl/uart.vhd \
       --intent verification/uart.intent \
       --req requirements/uart.req \
       --reg-map regmaps/uart_regmap.xlsx
```

### Multi-block SOC — one spreadsheet per designer

```
my_soc/
    uart/uart_regmap.xlsx    ← UART designer maintains
    gpio/gpio_regmap.xlsx    ← GPIO designer maintains
    spi/spi_regmap.xlsx      ← SPI designer maintains
    pssgen.toml              ← verification lead maintains

pssgen  ← generates all block RALs + soc_reg_map.sv
```

---

## CLI Reference

```
pssgen [--input <file>] [options]
```

When `pssgen.toml` is present, all settings load automatically. `--input` is optional when the toml specifies it.

| Flag | Default | Description |
|---|---|---|
| `--input <file>` | from toml | HDL source (.v, .sv, .vhd, .vhdl) |
| `--intent <file>` | auto-detected | SNL intent file. Auto: `<stem>.intent` |
| `--req <file>` | auto-detected | Requirements file. Auto: `<stem>.req` |
| `--reg-map <file>` | auto-detected | Register map (.xlsx). Auto: `<stem>_regmap.xlsx` |
| `--no-intent` | off | Suppress auto-loading of intent file |
| `--no-req` | off | Suppress auto-loading of req file |
| `--top <n>` | largest module | Top-level module or entity name |
| `--out <dir>` | ./out | Output directory |
| `--sim <target>` | vivado | vivado \| questa \| generic \| icarus |
| `--retry <n>` | 3 | Maximum orchestrator retry attempts |
| `--no-llm` | off | Template-only mode. No API key required. |
| `--scaffold` | off | Generate `_generated.intent` and `_generated.req` |
| `--coverage-loop <n>` | 0 | Maximum closure iterations (0 = disabled) |
| `--coverage-db <file>` | from toml | Vivado XML coverage database |
| `--collect-results <file>` | off | Read simulator results and update VPR RTL_Status column |
| `--config <file>` | auto | Explicit pssgen.toml path |
| `--dump-ir` | off | Write IR snapshot to `<out>/ir.json` |
| `--verbose` | off | Print file resolution and pipeline steps |

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Checker failure — retries exhausted |
| 2 | Parse failure — HDL could not be parsed |
| 3 | Configuration error |

---

## Working with Requirements

### Import from a Word or Excel source document

If your requirements live in a controlled Word SRS or Excel workbook, bootstrap the VPR in one command:

```bash
# From Word (.docx) — extracts requirement IDs and statement text
pssgen import-reqs --from word docs/UART-RS-001.docx --out ip/uart/uart_vplan.xlsx

# From Excel (.xlsx) — expects ID and description columns
pssgen import-reqs --from xlsx requirements/uart_reqs.xlsx --out ip/uart/uart_vplan.xlsx
```

The generated VPR is a starting point. Review it, fill in the `Covered_By` and `Test_Name` columns, and set `Disposition` for any requirement that is out of scope for simulation (`WAIVED`). pssgen never overwrites a VPR that already exists.

### Manual VPR path

Copy `docs/pssgen_vpr_template.xlsx`, rename it to match your IP (`uart_vplan.xlsx`), and populate it directly. The template includes column headers, dropdowns, conditional formatting, and a Summary sheet with status counters.

Key columns to populate for gap analysis:

| Column | Purpose |
|---|---|
| `Req_ID` | Requirement identifier (e.g. `UART-BR-001`) |
| `Requirement` | Requirement statement text |
| `Covered_By` | Coverage item ID cross-reference (e.g. `COV-001`) |
| `Verification_Method` | sim / post-silicon / inspection / analysis |
| `Disposition` | blank = open, `WAIVED` = out of scope |

A blank `Covered_By` on a non-waived requirement fires a **Direction A ERROR** in the gap report. Fill it to close the gap.

### Configure pssgen.toml

```toml
[project]
name = "uart"

[input]
vplan = "uart_vplan.xlsx"

[output]
dir = "tb"

[[sources]]
hdl = "vhdl/uart.vhd"

[[register_maps]]
source = "uart_regmap.xlsx"
format = "simple_block"
```

Then:

```bash
pssgen   # reads toml, VPR, and HDL — generates all artifacts
```

### Gap report

The gap report (`<design>_gap_report.txt`) records two directions:

- **Direction A ERROR** — requirement in VPR with no `Covered_By` entry and `Disposition` ≠ WAIVED
- **Direction B WARNING** — coverage item in VPR with no traceable requirement

Waived items appear in the report with their rationale but are not counted as gaps. The report is suitable as a verification closure argument for DO-254 Level C/D and similar compliance programs.

---

## Register Map Format

pssgen accepts three register map formats, auto-detected from the spreadsheet structure.

### simple_block — your designer's existing spreadsheet

Single sheet, 15 columns. This is the format designers already produce. No reformatting required. Three optional columns (`base_address`, `req_id`, `pss_action`) can be added at the right edge of your existing file without disturbing anything else.

Six real-world block fixtures are included in `tests/fixtures/`:

```
gpio_regmap_simple.xlsx    ← AXI GPIO
uart_gpio_regmap_simple.xlsx ← UART + GPIO (two blocks)
i2c_regmap_simple.xlsx     ← I2C
spi_regmap_simple.xlsx     ← SPI master
pwm_regmap_simple.xlsx     ← PWM
timer_regmap_simple.xlsx   ← Timer
```

### full_block — pssgen extended format

Four sheets: Globals, Blocks, RegisterMap (20 columns with full metadata), Enums. Use this format when you need per-field coverage control, HDL backdoor paths, or PSS action names. The template is at `docs/pssgen_regmap_template.xlsx`.

### system — multi-block reference

Two sheets: System (project globals) and Blocks (file references with base addresses). Each block keeps its own spreadsheet. The system sheet tells pssgen where to find each one and where it lives in the address map.

---

## Architecture Overview

```
HDL source + register map / requirements doc / VPR
            │
            ▼
    ┌────────────────────────────────────┐
    │  Parser Layer (Layer 1)            │
    │  verilog / vhdl / intent / req /   │
    │  regmap parsers                    │
    └────────────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │  IR (Layer 2) — append-only        │
    │  ports, register_map, req IDs,     │
    │  intent, waivers, gaps             │
    └────────────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │  Orchestrator — retry loop owner   │
    └────────────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │  Agents (Layer 3)                  │
    │  structure_gen  pss_gen  ral_gen   │
    │  scaffold_gen   gap_agent          │
    │  coverage_reader  closure_gen      │
    └────────────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │  Checker (Layer 4) — 3-tier        │
    │  structural / syntax / smoke       │
    │  UVM + PSS + RAL checks            │
    └────────────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │  Emitters (Layer 5)                │
    │  vivado  questa  generic_c         │
    └────────────────────────────────────┘
            │
            ▼
    ./out/  UVM .sv + PSS + RAL .sv + C + scripts + gap report
```

Five inviolable design principles:

- The orchestrator owns the retry loop. Agents never retry themselves.
- The IR is append-only. Fields are added; existing fields are never renamed or removed.
- Templates constrain the LLM. Jinja2 templates provide structural skeletons; the LLM fills design-specific content only.
- The checker's external contract is frozen. Internal checks grow without changing the orchestrator interface.
- The emission layer is the only simulator-aware layer. Adding a new simulator target requires one new emitter only.

---

## Installation

```bash
git clone https://github.com/BelTechSystems/pssgen.git
cd pssgen
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=your_key_here   # not required for --no-llm mode
```

**Python 3.11 or later required** (uses `tomllib` from the standard library).

**openpyxl is required for register map support:**

```bash
pip install openpyxl
```

---

## Running the Tests

```bash
# All tests except end-to-end (no API key or simulator needed)
python -m pytest tests/ --ignore=tests/test_e2e.py -v

# End-to-end tests (requires ANTHROPIC_API_KEY and xvlog)
python -m pytest tests/test_e2e.py -v
```

156 tests across 17 test modules. All phases covered.

---

## Human Authorship

pssgen is built with AI assistance. The architecture, design decisions, and domain expertise are human-authored by S. Belton, BelTech Systems LLC. A record of 19+ human creative decisions — including why PSS is the right IR, why the per-block spreadsheet format matches real engineering practice, and why the orchestrator owns the retry loop — is maintained in `DECISIONS.md`.

For background on why this tool was built:

> *"I spent years as the IP library custodian for a major aerospace company... projects would rather clone an IP block and own it than participate in the shared library. I think the answer is portable verification intent."*

---

## Contributing

pssgen is open source (MIT license). Contributions welcome — particularly:

- HDL parser improvements (VHDL, SystemVerilog edge cases)
- PSS model generation prompt improvements
- Coverage database readers (Questa UCDB — see OI-12)
- IP-XACT XML register map input (see OI-23)
- Requirements document importers (see OI-28, OI-29)

**Read `DESIGN.md` before contributing.** The architectural decisions recorded there explain *why* the code is structured as it is. Understanding the design rationale prevents well-intentioned changes that violate core principles (IR append-only policy, orchestrator owns retry logic, emission layer is simulator-aware only).

---

## Open Items

Key deferred features tracked in the SDS (OI list):

| ID | Item |
|---|---|
| OI-12 | Questa UCDB binary reading (requires vcover or pyucis) |
| OI-23 | IP-XACT XML register map input |
| OI-24 | Full RAL integration into UVM test and scoreboard |
| OI-28 | VPR `--collect-results` back-annotation: write simulator pass/fail into VPR RTL_Status column |
| OI-29 | Word SRS importer: `import-reqs --from word` CLI command and .docx paragraph parser |
| OI-30 | VPR diff/merge: detect added/removed requirements across runs without overwriting engineer data |

---

## License

MIT License — BelTech Systems LLC, 2026. See `LICENSE` for details.

---

## Status

**Current release: v4c**

156 tests passing. Full pipeline from HDL through UVM RAL model and system assembly. Real-world register map fixtures for GPIO, I2C, SPI, PWM, TIMER, and UART validated against the simple_block format.