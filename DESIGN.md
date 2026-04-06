# pssgen Design Rationale

This document records *why* the tool is designed as it is. Code explains what.
This document explains why. Read this before refactoring anything significant.

The companion changelog for each phase is maintained in the SDS
(`docs/pssgen_sds.docx`). Human authorship decisions are in `DECISIONS.md`.

---

## Why PSS as the Intermediate Representation

The verification tool space in 2025-2026 is crowded at the UVM scaffold generation
layer. Siemens Questa Agentic Toolkit, MooresLabAI, and ChipAgents all generate
initial UVM testbenches. None of them solve the two real problems:

1. PSS adoption is blocked by onramp friction, not by capability limits.
2. Coverage closure after scaffold generation is still manual.

PSS (Accellera Portable Stimulus Standard v3.0, August 2024) is the right
abstraction because it defines verification intent once and lets it execute across
simulation, FPGA prototyping, and post-silicon environments. Using PSS as the IR
means pssgen is complementary to enterprise tools (Siemens Questa, Cadence Perspec)
rather than competing with them. The tool feeds them — it does not replace them.

This positioning is deliberate and must be preserved. Do not design pssgen to
replace simulator vendor tooling. Design it to be the upstream layer that makes
their tooling accessible to engineers who cannot afford or justify an enterprise
license for an initial PSS workflow.

---

## Why the Orchestrator Owns the Retry Loop

Early designs considered putting retry logic inside each agent. This was rejected
for three reasons:

1. Agents are stateless by design. They accept an IR and a fail reason and produce
   artifacts. That simplicity makes them testable in isolation.
2. Retry policy (max attempts, backoff, cost guardrails) is a system concern, not
   an agent concern. It will change as the tool matures. Centralizing it in the
   orchestrator means changing it in one place.
3. The fail reason from the checker is the critical context injection that
   makes retries useful. The orchestrator is the natural place to wire checker output
   to agent input on the next attempt.

---

## Why the IR is Append-Only

The IR is the contract between all components. If a parser adds a field and the v0
emitter doesn't know about it, the emitter must still work — it just ignores the
unknown field. If the IR allowed field renames or removals, v0 components would
break when v1 adds new parsers or agents.

Append-only with Optional fields and None defaults is the specific mechanism:
new fields don't break old components because old components never read them.
This is the same principle as backward-compatible API versioning.

---

## Why Templates Constrain the LLM

Unconstrained LLM generation of UVM produces structurally varied output. The
checker's tier-1 structural checks would fail frequently, driving up retry
counts and LLM costs. Templates solve this by providing the structural skeleton
that the checker knows how to check — the LLM fills only the dynamic content
(class names derived from the design name, port signal bindings, interface
signal wire-ups). Tier-1 failures become rare. When they occur, the fail reason
is specific and the retry prompt is targeted.

---

## Why the Emission Layer is the Only Simulator-Aware Layer

Simulator-specific knowledge (xvlog flags, Tcl script structure, UCDB paths,
vsim invocation) is volatile. Vivado changes its build script format between
major releases. Questa changes flags. If simulator-specific strings are scattered
through the codebase, every tool update requires searching the entire codebase
for affected code. Centralizing in emitters/ means tool updates touch one file.

This also means adding a new simulator target (VCS, Aldec, ModelSim) requires
writing one new emitter and nothing else. No changes to the orchestrator, IR,
agents, or checker.

---

## Why RAL Generation is Always Template-Only

UVM RAL model structure is highly constrained. A `uvm_reg_block` has exactly one
`build()` function. Registers are created with `type_id::create()`. Fields are
configured with `.configure()`. The structure is deterministic given the register
map data. An LLM adds no value here and introduces risk of generating structurally
incorrect RAL code. Template-only generation applies regardless of the `--no-llm`
flag. See DECISIONS.md D-018.

---

## Why One _reg_block.sv Per Block

pssgen generates one SystemVerilog file per design block rather than one monolithic
RAL file. This matches how register maps are developed in practice — each designer
maintains their own block spreadsheet independently. A monolithic RAL file creates
a configuration management problem: any change to any block requires regenerating
and re-reviewing the entire file. Per-block generation means the UART designer's
RAL file is independently versionable from the GPIO designer's. See DECISIONS.md
D-020.

---

## Why System Assembly Uses add_submap()

The system-level register assembly uses `add_submap()` rather than flattening all
registers into a single `uvm_reg_map` with individual `add_reg()` calls. This
preserves the block boundary in the register model — a test can access
`uart.reg_map` or `gpio.reg_map` independently. Block-level register sequences
written for standalone verification run unchanged in the system test. The flat
approach loses this reusability. See DECISIONS.md D-021.

---

## Why the Simple_block Spreadsheet Format

pssgen accepts the 15-column spreadsheet format that designers already produce,
requiring no reformatting. Three optional columns (`base_address`, `req_id`,
`pss_action`) extend the existing file at the right edge. This decision was
validated against six real-world block spreadsheets — GPIO, I2C, PWM, SPI, TIMER,
UART — all of which passed validation with no structural issues. See DECISIONS.md
D-019.

Base address is inherited row-to-row from the most recent non-blank value in
column 16. Default is 0x0000_0000 when the column is absent entirely. This
matches how engineers actually fill in spreadsheets — write a value at the top
of a block and leave it implied for subsequent rows.

---

## Why Open Source (MIT)

A solo maker cannot compete with funded startups and incumbent EDA vendors on
engineering resources. The competitive advantage is domain expertise —
specifically, the insight that PSS is the right IR for AI-generated verification
and the knowledge to implement the PSS model correctly. That expertise is
expressed in the design decisions, the templates, and the checker checks.
It cannot be replicated quickly by an organization without hardware verification
depth.

Open source with MIT license means:
- Large organizations can adopt and build on the tool without legal friction.
- Academic researchers can cite and extend it.
- The community (r/FPGA, EDABoard) maintains and improves it.
- The effect is measured in years of citation and adoption, not in revenue.

The lasting effect of this tool is not a product. It is infrastructure that
teaches the mid-market how to use PSS with AI assistance. That effect compounds
over time in a way that a closed product cannot.

License review is deferred to v1.0 — consider Apache 2.0 for the explicit patent
grant. See DECISIONS.md D-002.

---

## Why the Walking Skeleton Approach

The most common failure mode for solo tool makers building large tools is that the
tool grows unwieldy before there is any end-to-end proof of life. Feature branches
accumulate. The integration point is deferred. By the time all the pieces exist,
the integration is the hardest part and motivation is exhausted.

The walking skeleton solves this by ensuring the pipeline is real and working at
the smallest possible scope before any scope is added. The counter goes in. The
UVM scaffold comes out. xvlog says it compiles. Every subsequent phase adds to a
working system, not a partially integrated one.

The choice of an 8-bit up/down counter as the v0 canonical case is deliberate:
- Simple enough that the parser can be written in a day
- Rich enough that the generated testbench has real content (ports, clock, reset,
  control signals, observable output)
- Universally understood — every hardware engineer knows what it is

---

## Why Claude Chat + Claude Code as the Development Environment

This architecture was developed in Claude chat before a line of code was written.
The chat session is the systems definition process: market analysis, architectural
trade-offs, strategic positioning, component interface design, and phase planning.

Claude Code handles implementation with the full file tree and test runner in view.
The risk is context drift — Claude Code does not see the design rationale unless
it is in the repo. CLAUDE.md, DESIGN.md, DECISIONS.md, and the SDS exist
specifically to prevent that drift. When Claude Code suggests something that
conflicts with a design decision recorded here, the document wins.

Design decisions are made in Claude chat. Implementation is done in Claude Code.
The documents are the bridge.

**Git policy:** Claude Code never runs `git push` autonomously. Commit freely.
Push only when explicitly instructed.

---

## Phase Gate Rules

No phase begins until the previous phase satisfies all of the following:

1. All tests from the previous phase pass without modification.
2. The end-to-end test for the current phase passes.
3. The new component has its own isolated unit tests.
4. The IR changes are backward-compatible (no renames, no removals).
5. The checker external interface is unchanged.

These gates are not bureaucracy. They are the mechanism that keeps a solo maker
from discovering integration problems six phases deep with no clean rollback point.

---

## Notes and Open Items

**Note 1 — generic_c.emit() behavior**
When running `--sim generic`, the output directory contains both the UVM `.sv`
files and the C file. This is correct for now — the engineer gets everything.
In a future phase, the generic target may want to suppress `build.tcl` since it
is only meaningful to Vivado users.

**Note 2 — PSS tier-2 elaboration (OI-10)**
No pip-installable open-source PSS parser exists as of v4. PSSTools/pssparser
(github.com/PSSTools/pssparser) is the candidate when it becomes pip-installable.
Until then, PSS validation is tier-1 structural only.

**Note 3 — Questa UCDB reading (OI-12)**
Questa UCDB binary format reading is deferred. Requires `vcover` command or
`pyucis` library. Current Questa closure scripts assume Vivado-compatible XML path.

**Note 4 — Full RAL integration (OI-24)**
The RAL block is generated but not wired into the UVM test or scoreboard. The
engineer instantiates the RAL block manually in their test. Full integration —
wiring the RAL into the test, agent, and scoreboard — is deferred.

**Note 5 — IP-XACT input (OI-23)**
IP-XACT XML register map input is planned for v5b. Deferred to allow v5a
(requirements import) to ship first. Open-source IP repositories (OpenTitan,
LowRISC, PULP Platform) provide real IP-XACT test fixtures.

**Note 6 — DOORS integration (OI-15)**
DOORS integration is deferred pending access to a real DOORS export file.
DOORS exports to both Word and Excel, so v5a importers provide indirect DOORS
support in the interim.

**Note 7 — Column mapping (OI-27)**
A future enhancement to allow engineers to map arbitrary spreadsheet column names
to pssgen fields via pssgen.toml, enabling acceptance of any existing spreadsheet
format without renaming columns.

---

## License Decision Record

Current license: MIT (BelTech Systems LLC, 2026).

MIT was chosen for maximum adoption with zero legal friction. Apache 2.0 was
considered and has advantages: explicit patent grant and patent retaliation clause,
which may ease enterprise legal review at aerospace primes and defense contractors
— pssgen's primary target audience.

Decision: revisit at v1.0 release. If a target enterprise customer flags the patent
grant as a blocker, switch to Apache 2.0 at that boundary. As sole author,
relicensing requires no contributor consent until external contributions are
accepted.
