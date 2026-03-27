# pssgen Design Rationale

This document records *why* the tool is designed as it is. Code explains what.
This document explains why. Read this before refactoring anything significant.

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

## Why Claude Chat + VSCode as the Development Environment

This architecture was developed in Claude chat before a
line of code was written. The chat session is the systems
definition process: market analysis, architectural
trade-offs, strategic positioning, component interface
design, and phase planning.

VSCode Chat handles implementation with the full file
tree and test runner in view. The risk is context drift —
VSCode Chat doesn't see the design rationale unless it is
in the repo. CLAUDE.md, DESIGN.md, and SDS.md exist
specifically to prevent that drift. When the AI suggests
something that conflicts with a design decision recorded
here, the document wins.

Design decisions are made in chat. Implementation is done
in VSCode. The documents are the bridge.

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

## Notes

Note 1:
dispatch.py — extension-to-parser routing helper shared by
cli.py and orchestrator.py. Consider moving to parser/
dispatch.py if the parser package grows in v1b+.

Note 2:
OI-10: PSS tier-2 elaboration check — deferred. No pip-installable
open-source PSS parser exists as of v1b. PSSTools/pssparser
(github.com/PSSTools/pssparser) is the candidate when it becomes
pip-installable. Until then, PSS validation is tier-1 structural only.

---

## Companion Changelog (v1 Reality)

This section mirrors the SDS addendum in plain text so code reviewers can
inspect scope changes directly in git diffs without opening the .docx.

### v1a — VHDL Parser Scope (Implemented)

- Module: parser/vhdl.py
- Supported port types:
   - std_logic -> width 1
   - std_logic_vector(N downto 0) -> width N+1
   - std_logic_vector(0 to N) -> width N+1
- Port mode mapping to IR:
   - in -> input
   - out -> output
   - inout -> inout
   - buffer -> output
- Integer generics are extracted into IR.parameters as string defaults.
- Role classification matches parser/verilog.py heuristics:
   clock, reset_n, reset, control, data.
- Unsupported VHDL port types raise ParseError naming both type and port.

### v1a — Extension-Based Parser Dispatch (Implemented)

- Module: parser/dispatch.py
- Dispatch mapping:
   - .v -> parser.verilog.parse
   - .sv -> parser.systemverilog.parse
   - .vhd/.vhdl -> parser.vhdl.parse
- CLI validates extension dispatch and exits code 3 on unsupported extensions.
- Orchestrator parses through shared dispatch to avoid duplicated routing logic.

### v1b — PSS Model Generator Agent (Implemented)

- Module: agents/pss_gen.py
- Public interface:
   generate_pss(ir, fail_reason=None, no_llm=False) -> str
- Template path: templates/pss/component.pss.jinja
- no_llm=True renders template-only output with no API call.
- no_llm=False renders skeleton first, then prompts LLM to fill constraints and
   coverage placeholders.
- Generated source is stored in ir.pss_model and emitted as <design_name>.pss.

### v1b — Checker Integration for PSS (Implemented)

- Module: checkers/verifier.py
- Tier-1 PSS structural checks now apply when .pss artifacts are present.
- Required content checks:
   - contains "component"
   - contains "action"
   - contains design_name

### v1b — Open Issue OI-10 (Formal)

- PSS elaboration/syntax parsing in tier-2 remains deferred.
- Rationale: no pip-installable open-source PSS parser is currently viable for
   CI integration.
- Impact: PSS validation is tier-1 structural only in v1b.
- Follow-up: add a PSS elaboration tier when a stable parser/elaborator becomes
   automation-ready.

### v2a — Structured Natural Language Intent (Implemented)

- Flag: --intent <file> (.intent extension)
- IR field: ir.pss_intent (Optional[str], append-only)
- Format: free-form sections, no schema enforcement.
  Preferred headings: reset behavior, counting sequences,
  coverage goals, corner cases, constraints.
  Any heading is accepted — the LLM maps intent to PSS
  by semantic understanding, not by validation.
- When present: pss_gen includes intent in LLM prompt
  and preserves it as a comment block in the PSS model.
- When absent: IR-only inference (existing behavior).

---

## License Decision Record

Current license: MIT (BelTech Systems LLC, 2026).

MIT was chosen for maximum adoption with zero legal
friction. Apache 2.0 was considered and has advantages:
explicit patent grant and patent retaliation clause,
which may ease enterprise legal review at aerospace
primes and defense contractors — pssgen's primary target
audience.

Decision: revisit at v1.0 release. If a target
enterprise customer flags the patent grant as a blocker,
switch to Apache 2.0 at that boundary. As sole author,
relicensing requires no contributor consent until
external contributions are accepted.
