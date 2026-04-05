# pssgen Decision Record

This document records human creative and technical decisions
that shaped pssgen. It exists to establish the nature and
extent of human authorship in a tool that uses AI assistance
for implementation.

Each entry identifies: the decision, the human who made it,
the domain knowledge or judgment it required, and why AI
assistance alone could not have produced the same outcome.

Copyright (c) 2026 BelTech Systems LLC. All rights reserved.

---

## D-001: PSS as the intermediate representation

Decision: Use PSS (Accellera Portable Stimulus Standard)
as the IR rather than generating UVM directly.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Ten years of systems engineering
experience at a major aerospace company, combined with VHDL
design experience and UVM/UVMF verification experience.
Direct experience as an IP library custodian who observed
the re-verification problem across multiple programs. This
decision required knowing that PSS exists, understanding
what problem it solves, and recognizing that it was the
right abstraction for a tool targeting the mid-market.

Why AI could not have made this decision alone: AI tools
available at the time of design did not identify PSS as the
missing piece in the verification tool landscape. The
insight that PSS adoption is blocked by onramp friction
rather than capability limits came from direct professional
experience with enterprise EDA tooling costs and the
behavior of aerospace programs that avoided PSS because
of those costs.

---

## D-002: Open source MIT license targeting aerospace adoption

Decision: Release under MIT license rather than a more
restrictive license or a commercial model.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Understanding of how aerospace
and defense programs evaluate and adopt open-source
software. Knowledge that enterprise legal departments
approve MIT-licensed dependencies more readily than GPL
or LGPL. Understanding that the competitive advantage
of pssgen is domain expertise embedded in templates and
design decisions, not the implementation code itself.

Why AI could not have made this decision alone: The choice
requires judgment about the target market's procurement
behavior, legal review practices, and the strategic value
of community adoption versus revenue generation. These are
business and organizational judgments, not technical ones.

---

## D-003: Five-layer pipeline architecture

Decision: Separate the pipeline into parser, IR, agents,
checker, and emitter layers with strict contracts between
them.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Systems engineering discipline
applied to software architecture. The layer boundaries
reflect the author's experience with IP library management
— specifically, the insight that simulator-specific
knowledge must be isolated in the emission layer so that
adding a new simulator target requires no changes to
verification logic. This mirrors the portability principle
in the PSS standard itself.

Why AI could not have made this decision alone: The
specific layer boundaries chosen reflect professional
judgment about which concerns change together and which
must be isolated. The decision to freeze the checker
external contract early reflects experience with interface
stability in long-lived engineering tools.

---

## D-004: Checker renamed from shim

Decision: Name the validation layer "checker" rather than
"shim."

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: UVM methodology experience.
"Checker" is the established UVM term for a component that
validates structural or protocol correctness. "Shim" is a
software engineering term for a compatibility adapter,
which is not what this component does. The rename reflects
domain vocabulary correctness.

Why AI could not have made this decision alone: Required
knowledge of both software engineering vocabulary and UVM
methodology vocabulary to identify the mismatch and select
the correct term.

---

## D-005: Structured natural language intent files

Decision: Accept verification intent as structured natural
language (.intent files) rather than YAML, JSON, or a
formal grammar.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Ten years of systems engineering
experience with requirements management tools including
IBM DOORS. Familiarity with how engineers actually write
requirements in practice — in natural language organized
by topic, not in structured data formats. Understanding
that the barrier to PSS adoption includes the learning
curve of any new formal language, and that reducing that
barrier required meeting engineers where they already work.

Why AI could not have made this decision alone: The
decision reflects a deliberate trade-off between machine
parseability and human adoption friction. The judgment
that engineers would adopt a natural language approach
more readily than a formal schema came from professional
experience with how verification teams respond to new
tooling requirements.

---

## D-006: Requirement ID auto-detection by regex pattern

Decision: Detect requirement ID schemes automatically
from the intent file rather than requiring the user to
configure a prefix.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with real aerospace
program requirement ID schemes across multiple programs.
Knowledge that ID schemes vary by organization, by program,
and by requirement type (SYS-REQ, FUNC-REQ, IF-REQ,
PERF-REQ, VER-REQ, and many others). Understanding that
a tool requiring prefix configuration would fail in
programs with complex or multi-level schemes.

Why AI could not have made this decision alone: Required
knowledge of the actual variety of requirement ID schemes
used in real aerospace and defense programs, combined with
the judgment that auto-detection was preferable to
configuration for adoption reasons.

---

## D-007: [CONFIRMED] / [WAIVED] disposition system

Decision: Add explicit disposition keywords to intent file
entries rather than treating all entries as active.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with requirements
management and verification closure in DO-254 programs.
Understanding that waiver documentation is a required
artifact in certification programs. Knowledge that without
an explicit ignore mechanism, repeated gap warnings train
engineers to ignore all warnings rather than respond to
meaningful ones — a pattern observed in real program
verification reviews.

Why AI could not have made this decision alone: The
disposition system reflects professional experience with
how verification teams behave under time pressure and how
certification auditors evaluate verification evidence.
The specific three-state model (GENERATED / CONFIRMED /
WAIVED) mirrors established practice in requirements
management tools.

---

## D-008: .req file never overwritten

Decision: Once a .req file exists, pssgen never overwrites
it under any circumstance.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with configuration
management in aerospace programs. Understanding that
engineer-owned artifacts in a certification program cannot
be silently modified by automated tools — doing so would
invalidate the audit trail. Knowledge that the .req file
represents human review work that must be preserved.

Why AI could not have made this decision alone: Required
understanding of configuration management discipline in
certified programs and the organizational consequences of
automated tools modifying controlled artifacts.

---

## D-009: Two-pass workflow with engineer review between passes

Decision: Design the tool for a deliberate two-pass
workflow where the engineer reviews and edits the
generated intent scaffold before pass 2, rather than
optimizing for fully automated single-pass generation.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Systems engineering discipline
applied to verification. Understanding that automated
coverage closure against AI-generated goals does not
constitute closure against a specification. Professional
experience with the difference between a verification
program that closes coverage and one that actually verifies
the design meets its requirements.

Why AI could not have made this decision alone: This
decision deliberately prioritizes human review over
automation convenience. It reflects a professional
judgment that the tool's value is in supporting human
verification engineers, not replacing their judgment.
An AI optimizing for automation would not have made this
choice.

---

## D-010: Three output levels (HDL only / + intent / + req)

Decision: Frame the tool's capability as three explicit
levels of rigor rather than a single mode with optional
features.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with how engineers
at different levels of process maturity adopt tools.
Understanding that DO-254 programs need Level 3 but
students and exploratory users need Level 1, and that
framing the tool as a continuum encourages adoption at
all levels rather than intimidating users with compliance
requirements.

Why AI could not have made this decision alone: Required
judgment about user adoption behavior across different
organizational contexts, from academic to certifiable.

---

## D-011: File header standard with human contribution evidence

Decision: Require a structured file header on every Python
file containing identification, description, function list,
dependencies, and change history.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with engineering
configuration management practices in aerospace programs.
Understanding that file-level change history is a
requirement in DO-254 and similar standards. Knowledge
that explicit human-authored function summaries in file
headers create audit evidence distinguishing human design
decisions from AI-generated implementation.

Why AI could not have made this decision alone: The
decision reflects professional judgment about what
constitutes sufficient evidence of human authorship for
copyright and compliance purposes. An AI tool optimizing
for code generation efficiency would not impose this
overhead. The standard exists because the human author
understands the audit context in which this tool will
be used.

---

## D-012: Three-tier coverage label hierarchy

Decision: Coverage labels for PSS covergroups follow
a three-tier hierarchy: requirement IDs (Tier 1),
intent section labels (Tier 2), IR port inference
(Tier 3). Higher tiers take priority. Every level
of human input produces correspondingly better output.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with requirements
traceability in DO-254 programs. Understanding that
named covergroups traceable to requirements are
auditable artifacts while generic covergroups are not.
Professional judgment that rewarding human input with
better output at every level encourages adoption of
the full requirements workflow.

Why AI could not have made this decision alone:
The hierarchy reflects a deliberate design choice to
meet engineers at their current level of process
maturity rather than requiring full requirements
compliance before the tool produces useful output.
This is a human judgment about adoption behavior and
tool design philosophy.

## D-013: File resolution verbose reporting

Decision: In verbose mode, pssgen reports the resolved
path and source label (explicit, auto-detected, from
pssgen.toml, or none) for every input file — HDL source,
intent, req, and config. In non-verbose mode, a single
hint is emitted when no intent file will be found.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with verification
tool adoption in long-running programs. When engineers
encounter unexpected behaviour — wrong intent file loaded,
wrong output directory — the first question is "what did
the tool actually use?" Verbose resolution reporting
answers that question without requiring debug flags or
source-code inspection. The distinction between
"auto-detected" and "from pssgen.toml" matters because
it tells the engineer whether the file was found by
convention or was explicitly configured.

Why AI could not have made this decision alone: The
decision reflects professional judgment about what
information engineers need to trust an automated tool in
a certification context. The specific labels chosen
(explicit, auto-detected, from pssgen.toml, none)
mirror the mental model engineers already use when
thinking about configuration layering, not the internal
implementation model.

---

## D-014: TOML project configuration file

Decision: Support a pssgen.toml project configuration
file that holds persistent settings. CLI flags override
for single runs. TOML chosen over YAML or INI for
standard library support (tomllib, Python 3.11+),
readability, and consistency with pyproject.toml which
pssgen users already know.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with how
engineering teams adopt tools in long-running programs.
Understanding that command-line friction — repeatedly
typing the same flags — is a common reason teams abandon
tools that are otherwise valuable. Knowledge of TOML
advantages over YAML for engineering tool configuration.

Why AI could not have made this decision alone: Reflects
professional judgment about the adoption lifecycle of
tools in aerospace programs where projects run for years
and the same IP blocks are verified repeatedly across
program phases.
```

---

## D-015: Four simulator targets for closure scripts

Decision: Support vivado, questa, icarus, and none as
closure script targets. Icarus Verilog chosen as the
open-source option — most widely installed, ships in
Linux package managers, runs on Windows via WSL.
none target supports pre-existing XML workflow without
invoking any simulator. Questa UCDB reading deferred
as OI-12.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Knowledge of open-source
EDA simulator landscape. Understanding that Icarus
is the most accessible free simulator for engineers
who cannot afford enterprise licenses. Experience
with how aerospace teams operate simulators in CI
and lab environments.

Why AI could not have made this decision alone:
Required judgment about which open-source simulator
has sufficient adoption to justify first-class support
versus which should be deferred. Icarus vs Verilator
vs GHDL is a domain-specific choice requiring knowledge
of the target audience's toolchain preferences.

---

## D-016: Two-mode requirements workflow

Decision: pssgen supports full requirements-driven
traceability when a complete .req file is provided,
and selective tagging when the engineer identifies
only the critical requirements in the .intent file.
Both modes use the same toolchain — the engineer
controls scope by choosing which lines to tag.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with both
mature DO-254 programs that have complete requirements
sets and earlier-stage programs or commercial designs
where formal requirements are partial or informal.
Understanding that a tool requiring full requirements
before producing useful output would fail in the
majority of real engineering contexts.

Why AI could not have made this decision alone:
Reflects professional judgment about the range of
process maturity across the target audience. The
decision to make full traceability and selective
tagging use identical syntax — just tag what matters
— reduces the barrier to starting with selective
tagging and graduating to full requirements as the
program matures.

## D-016: Two-mode requirements workflow

Decision: pssgen supports full requirements-driven
traceability when a complete .req file is provided,
and selective tagging when only critical behaviors
carry requirement IDs. Both modes use identical
syntax — the engineer controls formality scope by
choosing which lines to tag.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with both
mature DO-254 programs with complete requirements
sets and earlier-stage programs where formal
requirements are partial or informal. Professional
judgment that a tool requiring full requirements
before producing useful output would fail to achieve
adoption across pssgen's target audience.

Why AI could not have made this decision alone:
Required judgment about the range of process maturity
across the target audience. The decision to make full
traceability and selective tagging use identical syntax
reduces the barrier to starting informal and
graduating to formal as the program matures.

---

## D-017: Spreadsheet as primary register map format

Decision: The primary register map input format for
pssgen is a structured Excel spreadsheet (.xlsx) with
four sheets: Globals, Blocks, RegisterMap, and Enums.
IP-XACT XML is deferred to v5 as a secondary enterprise
input path. Plain English register intent in the .intent
file is supported as an acceleration aid for early
design stages but not for production use.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: A decade of systems
engineering experience combined with direct UVMF
verification experience at an aerospace company.
First-hand observation that verification engineers
in aerospace and defense programs receive register
maps as per-block spreadsheets, not as IP-XACT XML
or Word documents. Understanding that IP-XACT is
generated by enterprise EDA tools and is therefore
most useful to engineers who already have complete
tooling — not pssgen's primary target audience.

Why AI could not have made this decision alone:
Required direct professional experience with how
register maps are actually exchanged between design
and verification teams in real aerospace programs.
The choice of spreadsheet over IP-XACT reflects
observed industry practice, not the theoretical
standard. An AI reasoning from documentation would
have recommended IP-XACT as the "correct" format
without knowledge of how rarely it is used in
practice below the enterprise tier.

---

## D-018: RAL generation always template-only

Decision: UVM RAL generation (agents/ral_gen.py)
never calls the LLM. It is always template-only
regardless of the --no-llm flag. The no_llm
parameter is accepted for interface consistency
but has no effect.

Author: S. Belton, BelTech Systems LLC

Domain knowledge required: UVM RAL model structure
is highly constrained — a uvm_reg_block has
exactly one build() function, registers are
created with type_id::create(), fields are
configured with configure(). The structure is
deterministic given the register map data.
An LLM adds no value here and introduces risk
of generating structurally incorrect RAL code.

Why AI could not have made this decision alone:
Required professional judgment that the LLM
retry loop is valuable for UVM behavioral
scaffold generation (where creative variation
in constraint and coverage content is helpful)
but counterproductive for RAL generation (where
structural correctness is mandatory and variation
is harmful).

---

  ## D-019: Simple block spreadsheet format

  Decision: pssgen accepts a single-sheet 15-18
  column spreadsheet as its minimum viable block
  register map format. The first 15 columns match
  what designers already produce without any pssgen
  knowledge. Columns 16-18 (base_address, req_id,
  pss_action) are optional and extend an existing
  file without restructuring. Base address is
  inherited row-to-row from the most recently
  provided value, default 0x0000_0000 when absent.

  Author: S. Belton, BelTech Systems LLC

  Domain knowledge required: Direct UVMF verification
  experience receiving register maps as per-block
  spreadsheets from designers. Understanding that
  requiring engineers to adopt a new spreadsheet
  format is an adoption barrier, and that accepting
  their existing format with minimal extension is
  the correct tradeoff between tooling convenience
  and user friction.

  Why AI could not have made this decision alone:
  The choice to match the engineer's existing format
  rather than define a canonical pssgen-first format
  reflects professional experience with how tooling
  adoption fails in engineering organizations.
  Engineers will not restructure working documents
  to satisfy a tool. The tool must meet them where
  they are.
  
  The format was validated against six real-world block
  spreadsheets (GPIO, I2C, PWM, SPI, TIMER, UART) created
  independently by an engineer with RAL generation in mind.
  All six passed validation with no structural issues,
  confirming that the 15-column baseline matches actual
  engineering practice.
  
  ---
  
  ## D-020: One _reg_block.sv per block rather than
          one monolithic RAL file

Decision: pssgen generates one SystemVerilog file per
design block (_reg_block.sv) rather than combining all
blocks into a single monolithic RAL file.

Author: S. Belton, BelTech Systems LLC

Domain knowledge required: Experience with IP library
management in aerospace programs where individual blocks
are developed, versioned, and handed off independently.
Understanding that a monolithic RAL file creates a
configuration management problem — any change to any
block requires regenerating and re-reviewing the entire
file. Experience with UVM RAL architecture where per-block
uvm_reg_block subclasses are the standard unit of
reuse, matching how blocks appear in IP libraries.

Why AI could not have made this decision alone:
The monolithic approach is simpler to implement and
reduces file count. Choosing per-block generation
reflects professional judgment about how verification
artifacts are maintained across program lifecycles —
specifically, that the UART designer's RAL file should
be independently versionable from the GPIO designer's
RAL file, just as their HDL files are. An AI optimizing
for implementation simplicity would have produced a
single file. The per-block decision reflects
configuration management discipline from real program
experience.

Alternatives considered:
  Option A (chosen): One _reg_block.sv per block.
    Each block is independently versionable. Adding a
    new block to the system requires no changes to
    existing block files. Consistent with how IP library
    blocks are managed.
  Option B (rejected): One monolithic file containing
    all blocks. Simpler to implement. Creates coupling
    between independently maintained blocks. Any change
    triggers regeneration and review of the entire file.
    Inconsistent with IP library management practice.

---

## D-021: System assembly uses add_submap() rather
          than a flat unified address map

Decision: The system-level register assembly
(<project>_reg_map.sv) instantiates each block's
uvm_reg_block and registers it as a sub-map using
add_submap() rather than flattening all registers
into a single uvm_reg_map with individual add_reg()
calls.

Author: S. Belton, BelTech Systems LLC

Domain knowledge required: UVM RAL architecture
experience, specifically the distinction between
hierarchical register models (using add_submap) and
flat models (using add_reg at the system level).
Understanding that hierarchical models preserve the
block boundary in the register model — a test can
access uart.reg_map or gpio.reg_map independently,
enabling block-level register sequences to run
without modification in a system context. Knowledge
that flat models require all register accesses to be
re-expressed at the system level, losing the
block-level abstraction.

Why AI could not have made this decision alone:
The flat address map approach is simpler to understand
and generates a smaller SystemVerilog file. Choosing
add_submap() reflects professional judgment that
preserving the block boundary in the register model
enables IP reuse — block-level register sequences
written against uart_reg_block work identically
whether the block is instantiated standalone or as
part of a system. This matches how UVM RAL is used
in real UVMF-based verification environments where
block-level and system-level tests coexist. An AI
without this experience would likely choose the
simpler flat approach.

Alternatives considered:
  Option A (chosen): add_submap() per block.
    Preserves block boundary. Block-level sequences
    are reusable at system level without modification.
    System test accesses uart registers via
    regmodel.uart.ctrl.enable rather than
    regmodel.ctrl.enable — namespace is clear.
    Consistent with UVMF conventions.
  Option B (rejected): Flat unified map with add_reg()
    for all registers at system level. Simpler template.
    Loses block boundary. Block-level sequences cannot
    be reused at system level without modification.
    Register names from different blocks can collide
    if not carefully namespaced. Inconsistent with
    how enterprise RAL tools generate system maps.
  