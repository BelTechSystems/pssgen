# SOFTWARE DESIGN SPECIFICATION
## pssgen — AI-Driven PSS + UVM + C Testbench Generator

| Field | Value |
|---|---|
| Document ID | SDS-PSSGEN-001 |
| Version | 0.3 — v3 Coverage Closure and Traceability |
| Status | Draft |
| Date | 2026-03-28 |
| Classification | Open Source / Public |
| License | MIT — github.com/BelTechSystems/pssgen |

---

## Revision History

| Version | Date | Summary |
|---|---|---|
| 0.1 | 2026-03-26 | Initial draft. v0 walking skeleton scope. |
| 0.2 | 2026-03-27 | v1 and v2 addendum. VHDL parser, PSS generator, C emission, Questa emitter, SNL intent file. |
| 0.3 | 2026-03-28 | v3 addendum. Intent/req file system, coverage label hierarchy, bidirectional gap analysis, pssgen.toml config, coverage closure loop, 99 tests. Sections 2.2–2.9 added, IR schema updated, CLI reference updated, project structure updated. |

---

## 1. Introduction

### 1.1 Purpose

This Software Design Specification defines the architecture, components, interfaces, phased development plan, and design rationale for pssgen — an open-source, AI-driven command-line tool that generates verification artifacts from HDL source files and structured natural language verification intent. The tool uses the Accellera Portable Stimulus Standard (PSS v3.0) as its vendor-neutral intermediate representation, producing UVM 1.2-compliant SystemVerilog testbenches, C/C++ test cases, and requirement-traced coverage reports from a single PSS model.

This document covers releases through v3 (coverage closure and requirement traceability). It supersedes SDS-PSSGEN-001 v0.2.

### 1.2 Scope

pssgen accepts an HDL design file (Verilog, SystemVerilog, or VHDL), an optional structured natural language intent file (.intent), and an optional requirements file (.req) as input. It produces a PSS model, a UVM 1.2 testbench scaffold, C/C++ test cases, a requirement-traced gap report, and simulator closure scripts. A project configuration file (pssgen.toml) holds persistent settings. The tool runs with a single command when project files follow naming conventions.

### 1.3 Strategic Context

pssgen is differentiated on two dimensions:

**PSS as the portable IR.** Write verification intent once, execute across simulation, FPGA prototyping, and post-silicon environments without reimplementing the intent for each target.

**Portable requirement traceability.** The .req and .intent files travel with the IP, not with the program. When IP moves between programs, the next verification engineer inherits the verification intent and traceability alongside the RTL. This addresses a structural problem in aerospace and defense IP library management: traceability is done correctly inside programs but does not survive IP handoff because it is locked in program-specific requirements management tools (such as IBM DOORS) rather than in the IP package itself.

### 1.4 Human Authorship

pssgen is built with AI assistance. The architecture, design decisions, domain expertise, and creative direction are human-authored by S. Belton, BelTech Systems LLC. A complete record of human creative decisions is maintained in DECISIONS.md in the repository. That document contains 15 entries as of v3, each identifying the decision, the domain knowledge required, and why AI assistance alone could not have produced the same outcome.

Generated artifacts carry a human contribution notice identifying the engineer's HDL and intent files as the basis for copyright. The [GENERATED] / [CONFIRMED] / [WAIVED] disposition system in .intent files creates an explicit audit trail of human review activity distinct from AI-inferred content.

### 1.5 Definitions and Abbreviations

| Term | Definition |
|---|---|
| CLI | Command-Line Interface |
| DUT | Design Under Test |
| Gap Report | Bidirectional traceability report: reqs without intent (ERROR) and intent without reqs (WARNING) |
| HDL | Hardware Description Language (Verilog, VHDL, SystemVerilog) |
| IR | Intermediate Representation — vendor-neutral internal data model |
| PSS | Accellera Portable Stimulus Standard (current release: v3.0, August 2024) |
| RAL | Register Abstraction Layer (UVM register model) |
| SNL | Structured Natural Language — the .intent file format |
| UVM | Universal Verification Methodology (IEEE 1800.2, current: v1.2) |
| [CONFIRMED] | Disposition: engineer reviewed and accepts an intent entry |
| [GENERATED] | Disposition: AI-inferred entry awaiting human review |
| [WAIVED] | Disposition: engineer explicitly skips with documented reason |

---

## 2. Architecture

### 2.1 Five-Layer Pipeline

The five-layer architecture introduced in v0 is unchanged through v3. Data flows from HDL input through parser, IR, agents, checker, and emitter layers. v3 adds new agents (coverage_reader, closure_gen, gap_agent, scaffold_gen) and new parser modules (intent_parser, req_parser, context) without modifying any existing layer contracts.

| Layer | Name | Responsibility | Status |
|---|---|---|---|
| 1 | Parser | HDL, intent, req file parsing → IR | v3 — full |
| 2 | IR | Append-only vendor-neutral data model | v3 — extended |
| 3 | Agents | LLM + templates → PSS, UVM, C, gaps, scaffolds | v3 — full |
| 4 | Checker | 3-tier structural, syntax, smoke validation | v3 — unchanged |
| 5 | Emitters | Simulator-specific file output | v3 — unchanged |

The orchestrator owns the retry loop, sits above all five layers, and coordinates parse → generate → check → emit. The checker's external contract is frozen: `check(artifacts, sim_target) -> CheckResult`. Agents are stateless. The emission layer is the only simulator-aware layer.

### 2.2 File Convention (v3)

pssgen auto-detects context files by base name convention. When the input file is `counter.vhd`, pssgen automatically loads `counter.intent` and `counter.req` from the same directory if they exist. Explicit `--intent` and `--req` flags override the convention. `--no-intent` and `--no-req` suppress auto-detection. All resolution decisions are reported in verbose mode.

| File | Extension | Lifecycle | Priority |
|---|---|---|---|
| Intent file | .intent | Never written by pssgen. Auto-detected by stem. | Required for Level 2+ |
| Requirements file | .req | Written once on extraction. Never overwritten. | Optional at all levels |
| Project config | pssgen.toml | Written by engineer. Searched up directory tree. | Overridden by CLI flags |
| Gap report | _gap_report.txt | Written each pass. Overwritten on next run. | Output artifact |
| Closure script | run_closure_pass_N.sh/.bat | Written each closure pass. | Output artifact |

**Never-overwrite rule.** Once a .req file exists, pssgen never modifies it under any circumstance — even if it is empty or outdated. If the engineer wants a fresh extraction they delete the .req file manually.

### 2.3 Three Output Levels

pssgen produces output at three levels of rigor depending on what input files are present. All levels use the same command — the files present determine the output quality.

| Level | Input | Output | Use case |
|---|---|---|---|
| 1 | HDL only | IR-inferred PSS model, generic UVM scaffold, C tests | Exploration, learning, tooling demos |
| 2 | HDL + .intent | Intent-driven PSS, Tier 2 named covergroups, richer tests | Real verification work |
| 3 | HDL + .intent + .req | Req-traced PSS, gap report, closure scripts | DO-254 and compliance programs |

### 2.4 Coverage Label Hierarchy

PSS covergroup names follow a three-tier hierarchy based on what input is available. Higher tiers take priority. Every level of human input produces correspondingly better output.

| Tier | Condition | Covergroup name | Example |
|---|---|---|---|
| 1 | [REQ-xxx] ID present on intent line | cg_\<REQ_ID\> | cg_FUNC_REQ_113 |
| 2 | Intent section present, no req ID | cg_\<section\>_\<n\> | cg_coverage_goals_01 |
| 3 | IR port inference only | cg_inferred_\<port\>_\<n\> | cg_inferred_count_01 |

When a line carries both a req ID and belongs to an intent section, Tier 1 takes priority. The intent section is preserved as a comment inside the covergroup. Inferred labels (Tier 3) never generate Direction B warnings in the gap report — they are tool-generated, not human intent.

### 2.5 Requirement ID Auto-Detection

pssgen detects requirement ID schemes automatically from intent and req files using regex pattern matching. No configuration is required. The pattern is:

```
r'\[([A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*){1,4})\]'
```

Supported formats include [REQ-001], [SYS-REQ-001], [FUNC-REQ-001], [IF-REQ-001], [PERF-REQ-001], [VER-REQ-001], and any variant following the general pattern [UPPERCASE-SEGMENTS-NUMBER]. Disposition keywords [GENERATED], [CONFIRMED], and [WAIVED] are explicitly excluded — they contain no numeric segment. Mixed schemes in a single file are supported. Detected schemes are stored in `ir.requirement_schemes`. Coverage gap reports group gaps by scheme.

### 2.6 Disposition System

Intent file entries carry one of three disposition prefixes that create an explicit audit trail of human review.

| Disposition | Meaning | Pass 2 behavior | Gap report behavior |
|---|---|---|---|
| [GENERATED] | AI-inferred, awaiting review | Warn: unreviewed item | Flagged as unreviewed |
| [CONFIRMED] | Engineer reviewed and accepts | Generate PSS coverage goal | Reported against req ID if present |
| [WAIVED] | Engineer explicitly skips with reason | Skip — no coverage goal | Listed with reason, not counted as gap |
| (no prefix) | Engineer-written | Treated as [CONFIRMED] | Reported against req ID if present |

If any [GENERATED] lines survive into pass 2 without disposition, pssgen emits a non-fatal warning identifying the unreviewed lines.

### 2.7 Gap Report

The bidirectional gap report is written to `<design_name>_gap_report.txt` in the output directory on every run that has intent or req input. It contains four sections:

**ERRORS** — requirements in .req with no matching intent or coverage goal. Direction A. Highest severity. Must be resolved before claiming verification closure.

**WARNINGS** — intent entries or inferred covergroups with no matching requirement ID. Direction B. Traceability advisory.

**WAIVERS** — explicitly excluded items with documented reasons. Not counted as gaps regardless of coverage status.

**COVERAGE STATUS** — hit/miss status from simulation results when `--coverage-db` is provided. Covergroups are marked HIT (>=100% coverage), MISSED (<100%), or UNKNOWN (not in coverage XML).

A one-line console summary is printed to stdout. WAIVED items are never counted as errors.

### 2.8 Two-Mode Requirements Workflow

pssgen supports two requirement workflows, using identical syntax:

**Full requirements set.** The engineer populates `counter.req` with the complete requirements set — from DOORS, a specification document, or their own derivation. Every intent entry is tagged with a requirement ID. The gap report is a compliance-ready verification closure argument suitable for DO-254 programs. The requirement statements in the .req file provide the full specification text alongside each ID.

**Selective tagging.** The engineer has no formal requirements set, or only certain behaviors are compliance-relevant. They tag only the critical entries in the .intent file with requirement IDs. pssgen extracts those IDs automatically and writes a .req skeleton for the tagged items only. Tagged items get requirement-traced Tier 1 covergroups and appear in the formal gap report. Untagged items still generate Tier 2 coverage but are not tracked as requirements. Any untagged item can be promoted to a formal requirement by adding an ID — no other changes are needed. Same tool. Same files. The engineer controls how much is formal.

### 2.9 pssgen.toml Project Configuration

A `pssgen.toml` file at the project root holds persistent settings. The tool searches for it in the current working directory, the directory containing the input file, and up the directory tree to the filesystem root. CLI flags override any toml setting for a single run.

Priority chain: `toml defaults → toml settings → CLI flags`

```toml
[project]
name        = "up_down_counter"
description = "8-bit up/down counter with synchronous enable"

[input]
file    = "rtl/counter.vhd"
top     = "up_down_counter"
intent  = "verification/counter.intent"
req     = "requirements/counter.req"

[output]
dir = "./out"
sim = "vivado"

[generation]
retries  = 3
no_llm   = false
scaffold = false

[coverage]
loop = 0
db   = ""
```

When pssgen.toml is present and fully configured, the entire command line reduces to: `pssgen`

### 2.10 Coverage Closure Loop

When `--coverage-loop N` is specified, pssgen runs up to N closure iterations. Each iteration reads a Vivado XML coverage database (`--coverage-db`), updates the gap report with hit/miss status per covergroup, regenerates targeted PSS sequences for uncovered bins by injecting the gap context into the pss_gen LLM prompt, and writes a simulator-specific closure script.

Supported simulator targets for closure scripts: `vivado` (xsim batch flow), `questa` (vlog/vsim Makefile), `icarus` (iverilog/vvp shell script), `none` (pre-existing XML workflow, no simulator invoked). Scripts are written as both `.sh` and `.bat`.

When `--coverage-loop > 0` but no `--coverage-db` is provided, pssgen warns clearly, generates a pass-1 script for the engineer to run, and exits 0. This supports the use case of generating gap reports on a machine without a simulator installed.

OI-12: Questa UCDB binary format reading is deferred. Requires `vcover` command or `pyucis` library.

---

## 3. Intermediate Representation Schema

The IR is append-only. New fields are Optional with default values. Existing fields are never renamed or removed. Components that do not read a field ignore it — backward compatibility is always preserved.

| Field | Type | Description | Phase |
|---|---|---|---|
| design_name | str | Top-level module or entity name | v0 |
| hdl_source | str | Path to the input HDL file | v0 |
| hdl_language | enum | verilog \| systemverilog \| vhdl | v0 |
| ports | list[Port] | Name, direction, width, role for each port | v0 |
| parameters | dict | Name and default value for each parameter/generic | v0 |
| emission_target | enum | vivado \| questa \| generic | v0 |
| output_dir | str | Target directory for generated files | v0 |
| pss_intent | Optional[str] | Plain English intent content from .intent file | v2a |
| pss_model | Optional[str] | Generated PSS model source text | v1b |
| register_map | Optional[dict] | Register definitions for RAL generation | v4 |
| requirement_ids | list[str] | All [REQ-xxx] IDs found in intent file | v3b |
| requirement_schemes | list[str] | Detected prefixes: ["SYS-REQ", "FUNC-REQ"] | v3b |
| intent_waivers | list[dict] | Waived items with reasons and associated req IDs | v3b |
| intent_gaps | list[str] | Port names with no inferred intent | v3a |

---

## 4. Command-Line Interface

### 4.1 Invocation

```
pssgen [--input <file>] [options]
```

When `pssgen.toml` is present in the project directory, all settings are loaded automatically. `--input` is optional when pssgen.toml specifies `[input] file`. The minimal command for a fully configured project is:

```
pssgen
```

### 4.2 Arguments

| Argument | Default | Description |
|---|---|---|
| --input \<file\> | from toml or required | HDL source (.v, .sv, .vhd, .vhdl) |
| --intent \<file\> | \<stem\>.intent if present | SNL intent file. Overrides convention. |
| --req \<file\> | \<stem\>.req if present | Requirements file. Overrides convention. |
| --no-intent | off | Suppress auto-loading of intent file |
| --no-req | off | Suppress auto-loading of req file |
| --top \<n\> | largest module | Top-level module or entity name |
| --out \<dir\> | ./out | Output directory |
| --sim \<target\> | vivado | vivado \| questa \| generic \| icarus |
| --retry \<n\> | 3 | Maximum orchestrator retry attempts |
| --no-llm | off | Template-only mode. No API key required. |
| --scaffold | off | Generate _generated.intent and _generated.req |
| --coverage-loop \<n\> | 0 | Maximum closure iterations (0 = disabled) |
| --coverage-db \<file\> | from toml | Vivado XML coverage database path |
| --config \<file\> | pssgen.toml auto | Explicit project config file path |
| --dump-ir | off | Write IR snapshot to \<out\>/ir.json |
| --verbose | off | Print file resolution and pipeline steps |

### 4.3 Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success — all artifacts generated and verified |
| 1 | Checker failure — retries exhausted. Reason on stderr. |
| 2 | Parse failure — HDL source could not be parsed |
| 3 | Configuration error — invalid arguments or unsupported target |

### 4.4 Project File Layout

**Simplest layout — all files co-located:**

```
my_project/
    counter.vhd
    counter.intent    ← auto-detected
    counter.req       ← auto-detected
    pssgen.toml

pssgen
```

**Separated layout — RTL and verification separate:**

```
my_project/
    rtl/counter.vhd
    verification/counter.intent
    requirements/counter.req

pssgen --input rtl/counter.vhd \
       --intent verification/counter.intent \
       --req requirements/counter.req
```

---

## 5. Phased Development Roadmap

| Phase | Name | Key Deliverables | Tests | Status |
|---|---|---|---|---|
| v0 | Walking skeleton | Verilog → 7 UVM files + build.tcl | 13 | Complete |
| v1a | VHDL parser | VHDL entity → same IR as Verilog parser | 20 | Complete |
| v1b | PSS model generator | IR → PSS v3.0, tier-1 structural checker | 26 | Complete |
| v2a | SNL intent file | --intent flag, disposition markers | 29 | Complete |
| v2b | C test case emission | PSS model → C test functions | 34 | Complete |
| v2c | Questa emitter | Makefile + .sv files for QuestaSim | 41 | Complete |
| v3a | Intent scaffold | --scaffold, _generated.intent and .req | 57 | Complete |
| v3b | Requirement traceability | Three-tier labels, bidirectional gap report | 71 | Complete |
| v3c-a | Project config | pssgen.toml, auto-detection, resolution reporting | 80 | Complete |
| v3c-b | Coverage closure | Vivado XML reader, closure scripts, loop | 99 | Complete |
| v4 | Register / RAL | Plain English register intent → PSS → UVM RAL | — | Planned |
| v5 | DOORS integration | Import requirements directly from DOORS export | — | Roadmap |

---

## 6. Project Structure

```
pssgen/
  pssgen.toml              Project configuration (engineer-created)
  CLAUDE.md               Claude Code session guidance
  DESIGN.md               Architecture rationale and design decisions
  DECISIONS.md            Human authorship decision record (15 entries through v3)
  README.md               User-facing documentation
  LICENSE                 MIT License — BelTech Systems LLC 2026
  config.py               pssgen.toml loader and CLI merge logic
  cli.py                  argparse entry point
  orchestrator.py         Pipeline coordinator and retry loop owner
  ir.py                   IR dataclass (append-only through all phases)
  parser/
    dispatch.py           Extension-to-parser routing
    verilog.py            Verilog module/port extractor
    vhdl.py               VHDL entity/port extractor
    systemverilog.py      Stub → future
    intent_parser.py      .intent file parser, disposition and req ID extraction
    req_parser.py         .req file parser, statement and waiver extraction
    context.py            File resolution by stem convention or explicit flag
  agents/
    structure_gen.py      UVM scaffold agent (7 templates)
    pss_gen.py            PSS model agent, three-tier coverage label builder
    scaffold_gen.py       _generated.intent / _generated.req writer
    gap_agent.py          Bidirectional gap analysis, report writer
    coverage_reader.py    Vivado XML coverage parser
    closure_gen.py        Closure script generator (vivado/questa/icarus/none)
  checkers/
    verifier.py           3-tier checker (structural, syntax, smoke)
  emitters/
    vivado.py             .sv files + build.tcl + .pss
    questa.py             .sv files + Makefile + .pss
    generic_c.py          _pss_tests.c from PSS action regex
  templates/
    uvm/                  7 Jinja2 UVM templates + build_questa.mk.jinja
    pss/                  component.pss.jinja (named covergroup loop)
    c/                    test_functions.c.jinja
  tests/
    fixtures/             counter.v, counter.vhd, counter.intent,
                          counter.req, pssgen.toml, counter_coverage.xml
    test_checker.py       5 tests
    test_config.py        9 tests
    test_context.py       5 tests
    test_coverage_reader.py  4 tests
    test_closure_gen.py   6 tests
    test_emitter_c.py     5 tests
    test_emitter_questa.py   7 tests
    test_gap_agent.py     12 tests
    test_intent_parser.py 5 tests
    test_ir.py            2 tests
    test_orchestrator.py  1 test
    test_parser.py        5 tests
    test_parser_vhdl.py   7 tests
    test_pss_gen.py       14 tests
    test_req_parser.py    2 tests
    test_scaffold_gen.py  4 tests
    test_e2e.py           (gated — requires ANTHROPIC_API_KEY and xvlog)
  docs/
    pssgen_sds.docx       This specification
```

---

## 7. Non-Functional Requirements

| Requirement | Target | Notes |
|---|---|---|
| CLI startup time | < 1 second | Excluding LLM call latency |
| Single-pass generation | < 30 seconds | Single agent, single LLM call |
| Retry limit | 3 attempts default | Configurable via --retry or pssgen.toml |
| Python version | >= 3.11 | tomllib stdlib requires 3.11+ |
| External dependencies | Minimal | jinja2, anthropic SDK only |
| OS support | Linux, macOS, Windows | Windows tested natively without WSL |
| IR backward compatibility | Always | Append-only schema policy, enforced by convention |
| Simulator required | Optional | Tier-2 checker only; all other functions simulator-free |
| LLM required | Optional | --no-llm mode for CI and testing |
| License | MIT | BelTech Systems LLC, 2026 |
| Test coverage | 99 tests | All phases, e2e gated separately |

---

## 8. Open Items and Future Work

| ID | Phase | Item | Status |
|---|---|---|---|
| OI-10 | v1b+ | PSS tier-2 elaboration — PSSTools/pssparser not pip-installable as of v3 | Deferred |
| OI-11 | v2b+ | C artifact tier-2 syntax check via gcc --syntax-only | Deferred |
| OI-12 | v3c+ | Questa UCDB binary reading — requires vcover or pyucis library | Deferred |
| OI-13 | v4 | Register intent NLP — mapping plain English to PSS register constructs | Planned |
| OI-14 | v4 | UVM RAL generation from PSS register model | Planned |
| OI-15 | v5 | DOORS export import — read requirements directly from DOORS XML/CSV | Roadmap |
| OI-16 | all | LLM model selection and prompt version pinning strategy for reproducibility | Open |
| OI-17 | all | API cost guardrails for retry loops running in CI environments | Open |
| OI-18 | v3c+ | Icarus Verilog UVM library setup documentation | Open |
| OI-19 | future | License review at v1.0 — consider Apache 2.0 for explicit patent grant | Roadmap |

---

*End of document — SDS-PSSGEN-001 v0.3*
*Copyright (c) 2026 BelTech Systems LLC — MIT License*
