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

Author: S. Belvin, BelTech Systems LLC

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

Author: S. Belvin, BelTech Systems LLC

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

Author: S. Belvin, BelTech Systems LLC

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

This decision is further validated by direct observation
that in real aerospace and defense programs, register
maps are almost always developed and maintained as
individual per-block spreadsheets rather than as a
single unified system file. The per-block generation
approach matches the natural unit of work in these
programs.

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

Author: S. Belvin, BelTech Systems LLC

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
  
---
  
## D-022: import-reqs as a subcommand not a flag

Decision: Requirements document ingestion is a
separate subcommand (pssgen import-reqs) rather
than a flag on the main pipeline. The import is
a one-time operation that produces a .req file
for engineer review. The main pipeline then uses
that .req file exactly as it does today.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Understanding that
requirements ingestion and verification generation
are categorically different operations with
different error modes, different review requirements,
and different cadences. The import runs once when
the specification changes. The pipeline runs many
times during verification. Coupling them as flags
on one command conflates two distinct workflows.

Why AI could not have made this decision alone:
Reflects professional experience with how engineers
actually work with requirements documents — they
import once, review carefully, then iterate many
times on verification. The subcommand boundary
makes the review step explicit and mandatory.

## D-023: shall as the requirement discriminator

Decision: The Word document extractor uses "shall"
as the primary discriminator for requirement
statements. "Should" and "will" are not extracted
as requirements. Verification method statements
following the requirement are extracted and
associated with it.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Knowledge of MIL-STD-490,
DO-254, DO-178, and related defense and aerospace
standards that define "shall" as mandatory
requirement language. Ten years of systems
engineering experience writing and reviewing
requirements documents in these standards.
Understanding that "should" identifies a goal
(desirable but not mandatory) and "will" identifies
a statement of fact or future action rather than
a requirement.

Why AI could not have made this decision alone:
The distinction between "shall", "should", and
"will" in requirements language is a domain-specific
convention not derivable from general language
understanding. An AI without aerospace standards
experience would likely extract all three as
requirements, producing false positives that
contaminate the traceability chain.

---

## D-024: .req file represents verification cross-reference,
          not requirements document content

Decision: The pssgen .req file is a verification
cross-reference artifact maintained by the verification
engineer. It maps requirement IDs to verification methods
and closure status. It is NOT a copy of or replacement
for the requirements specification document. The
requirements specification (SRS, DRS) is a controlled
document that pssgen reads but never writes.

The import-reqs command extracts requirement IDs from
external sources to populate the .req skeleton. For
Word SRS documents, only requirement IDs and statement
text are extracted — verification method assignments
are left for the verification engineer to complete,
because verification methods are determined by the
verification engineer, not specified in the SRS.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Ten years of systems
engineering experience in aerospace programs operating
under NASA GSFC procedures (500-PG-8700.2) and ECSS
standards (ECSS-E-ST-20-40, ECSS-Q-ST-60-02C).
Direct experience with the document hierarchy:
requirements specification → verification plan →
verification cross-reference matrix → closure evidence.
Understanding that these are separate controlled
artifacts with separate authors, separate lifecycles,
and separate review obligations.

Why AI could not have made this decision alone:
Required knowledge of how aerospace verification
programs are actually structured under formal standards.
An AI without this background would conflate the
requirements document with the verification plan and
design a tool that conflates them too — producing
artifacts that do not match any real program's
document hierarchy and cannot be used in a compliant
program without rework.

---

## D-025: .req file is optional; waivers split by
          what is being waived, not by file type

Decision: The .req file is not required for pssgen
to run. The .intent file is the only required input
beyond the HDL source. The .req file has two valid
usage modes chosen by the engineer:

  Full mode — all requirements with verification
    methods and dispositions. Used when no external
    source document exists or when the engineer
    prefers a single flat text artifact.

  Campaign mode — only waived requirements. Used
    when requirements live in a controlled source
    document (.docx or .xlsx) and the engineer
    needs only to record which requirements are
    out of scope for the current simulation
    campaign.

Waivers are split by what is being waived:

  Waiver on a REQUIREMENT → lives in .req
    Records that a requirement is out of scope
    for this verification campaign. Carries a
    rationale. Does not remove the requirement
    from the source document.
    Example: [WAIVED] Cannot verify sub-cycle
             timing pre-silicon.

  Waiver on a COVERAGE ITEM → lives in .intent
    Records that the verification engineer has
    decided not to pursue a coverage goal.
    Carries a rationale. The item is excluded
    from gap counting.
    Example: WAIVED: INTENT-max-rate-silicon
             rationale: Physical layer out of scope.

Inline requirements in .intent are a stepping stone
for smaller designs or early-stage IP. The expected
migration path as a design matures is:
  .intent inline requirements
    → dedicated .req file (full mode)
      → controlled .docx source + .req campaign waivers

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with
verification campaign management in real aerospace
programs. Understanding that waiver documentation
serves two distinct purposes — excluding items from
the current campaign scope versus excluding items
from coverage tracking — and that conflating these
produces audit artifacts that satisfy neither
purpose. Direct experience with DO-254 compliance
reviews where the distinction between "not verified
in this campaign" and "coverage goal not pursued"
carries different implications for certification
credit.

Why AI could not have made this decision alone:
An AI optimizing for simplicity would put all
waivers in one place. The split reflects professional
judgment that requirement campaign waivers and
coverage intent waivers have different owners,
different review obligations, and different
implications for certification evidence. A
verification engineer owns coverage waivers.
The program verification plan owns requirement
campaign waivers. These must be separately auditable
artifacts. The split also reflects experience with
how the .req file role evolves across a design
lifecycle — a tool that requires a full .req file
from day one imposes ceremony that blocks adoption
on small IP blocks and early-stage designs.

Alternatives considered:
  Option A (chosen): .req optional; waivers split
    by subject. Engineer chooses full or campaign
    mode. Coverage waivers always in .intent.
    Requirement waivers always in .req.
    Clean ownership. Separately auditable.
  Option B (rejected): All waivers in .intent.
    Simpler for the engineer. Conflates requirement
    campaign scope decisions with coverage intent
    decisions. Produces a single artifact that
    mixes two distinct verification concerns.
    Cannot satisfy a DO-254 audit that treats
    these separately.
  Option C (rejected): .req required always.
    Forces ceremony on small designs. Blocks
    adoption. Contradicts the stepping-stone
    philosophy that makes pssgen accessible
    to engineers who are not already operating
    in formal verification programs.
	
---

## D-026: IP data sheet contains only information not
          available in any other artifact

Decision: The DATASHEET.md for each IP block is kept
deliberately short and contains only information that
has no other home in the artifact set:

  - Identity and maturity status at a glance
  - A copy-paste-ready instantiation example in both
    HDL languages — the only place this exists in
    runnable form
  - Known limitations and integration gotchas —
    engineering judgment accumulated from real use,
    not derivable from the specification
  - Synthesis results and power estimates across
    target devices and tool versions — not captured
    anywhere else in the artifact set
  - Tested-with versions — records what tool versions
    were actually validated, not aspirational support

The data sheet explicitly does not repeat:
  - Register map (lives in the spec and .xlsx)
  - Port list (lives in the VHDL/SV entity)
  - Functional block descriptions (live in the HDL
    file header)
  - Generic/parameter tables (live in the spec)
  - Interrupt source descriptions (live in the spec)
  - Requirements metrics (live in the gap report)
  - Coverage goals (live in the .intent file)
  - File inventory (lives in the git repository)

The resource utilization and power tables start empty.
Rows are added by the engineer after each synthesis
run. Target device and tool are left blank until an
actual run has been performed — pre-populated rows
with dashes imply the design has been validated on
that target when it has not.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience maintaining IP
libraries across multiple aerospace programs where
data sheets were routinely out of sync with the
actual implementation. The failure mode is always
the same: engineers copy the spec into the data sheet,
then the spec evolves and the data sheet does not.
Readers lose trust in the data sheet entirely.
Understanding that a short, non-redundant data sheet
that is always accurate is more valuable than a
comprehensive one that may be stale. Experience
with IP handoff between programs where the
instantiation example was the single most useful
artifact — engineers do not read specifications
before instantiating IP, they copy the example.

Why AI could not have made this decision alone:
The natural AI response to "create an IP data sheet"
is to produce a comprehensive document that
summarises all available information. That is what
most IP data sheets look like and what training data
reflects. The decision to actively remove information
that exists elsewhere — and to leave synthesis tables
empty rather than pre-populating them with dashes —
requires professional judgment about how engineers
actually use data sheets in practice and how
documentation rot happens in real IP libraries.
The insight that a copy-paste instantiation example
is the highest-value single artifact came from
direct observation of how engineers approach new IP
in program environments, not from documentation
theory.

Alternatives considered:
  Option A (chosen): Non-redundant data sheet.
    Contains only what is not elsewhere. Short,
    accurate, always current. Synthesis tables
    grow as real runs are completed.
  Option B (rejected): Comprehensive summary data
    sheet that reproduces key content from the spec,
    entity, and register map in condensed form.
    Immediately useful but immediately at risk of
    staleness. Every spec revision requires a
    corresponding data sheet update. Experience
    shows this discipline is not maintained under
    program schedule pressure.
  Option C (rejected): No data sheet — rely entirely
    on the spec and HDL artifacts. Loses the
    instantiation example and the synthesis results
    which have no other natural home. Makes IP
    adoption harder for engineers who need a quick
    reference without reading a full specification.
	
The data sheet is generated automatically by pssgen on
each pipeline run (agents/datasheet_gen.py). Sections
derived from the IR and artifact set are fully
regenerated. Sections containing engineer-entered data
(synthesis results, power estimates, integration notes,
tested-with versions) are preserved across runs using
a section-aware merge. The merge strategy mirrors the
never-overwrite principle of the .req file but allows
partial regeneration of derived content. A new revision
history entry is appended automatically on each run
that produces a changed output.

---

## D-027: VHDL and SystemVerilog implementations share
          a fixed interface contract but are free to
          diverge internally

Decision: When both a VHDL and SystemVerilog
implementation exist for the same IP block, the two
files are bound by a fixed interface contract and
are otherwise independent.

The interface contract — which is non-negotiable —
consists of:
  - Identical port names, directions, and widths
  - Identical parameter semantics and default values.
    The naming prefix differs by language convention
    (G_ for VHDL generics, P_ for SV parameters) but
    the logical parameter is the same: G_FIFO_DEPTH
    and P_FIFO_DEPTH describe the same design intent.
  - Identical register map behavior: same offsets,
    same reset values, same access types, same field
    semantics
  - Identical elaboration assertion boundaries: the
    same out-of-range conditions that cause the VHDL
    implementation to fail elaboration must also
    cause the SV implementation to fail
  - Identical failure conditions

The internal implementation — which is unrestricted —
includes:
  - Signal decomposition and naming (both use _s
    suffix but may structure internal logic differently)
  - Process and always_ff block organization
  - Type usage (VHDL unsigned vs SV logic [N:0])
  - Language-specific idioms (VHDL if-generate vs SV
    initial begin with $fatal)
  - Internal optimizations that exploit language
    strengths (SV packed arrays, VHDL record types)

This means the two files are drop-in compatible at the
system integration level — a system integrator can
choose either implementation and connect it to the
same AXI-Lite fabric with no change to the surrounding
design. The choice between VHDL and SV is a toolchain
and preference decision, not an interface decision.

The pssgen.toml points at one canonical HDL source per
project. Running pssgen against either file produces
equivalent IR, equivalent verification artifacts, and
equivalent gap reports. The data sheet instantiation
example covers both languages.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience with IP library
management across mixed-language programs where the
same IP block must be available in both VHDL and
SystemVerilog for different downstream consumers.
Direct experience with the failure mode of diverging
interfaces — a VHDL team changes a port width and
the SV team is not notified, breaking system
integration months later. Understanding that port
names and widths are the contract that system
integrators depend on, and that this contract must
be enforced explicitly rather than assumed. Knowledge
that the language-convention difference between G_
and P_ prefixes is well understood in the industry
and does not break drop-in compatibility in practice
because no synthesis or simulation tool compares
generic names across languages.

Why AI could not have made this decision alone:
The natural AI response is either to require
identical implementations in both languages (too
restrictive — loses the benefit of language-specific
optimization) or to allow complete independence (too
permissive — breaks system-level interchangeability).
The boundary drawn here — fixed interface, free
internals — reflects professional judgment from IP
library management experience about where the
contractual obligation actually lies. It also
reflects practical knowledge that the G_/P_ naming
difference is a non-issue in practice, which an AI
without industry experience would likely flag as a
compatibility concern and attempt to resolve by
imposing identical naming across both languages.

Alternatives considered:
  Option A (chosen): Fixed interface contract,
    free internals. Drop-in compatible. Language-
    optimized implementations. Interface enforced
    by pssgen parser verification (both must produce
    IR with identical port count, names, and widths).
  Option B (rejected): Identical implementations
    in both languages — direct mechanical translation.
    Loses the benefit of language-specific idioms.
    Produces SV that reads like translated VHDL,
    which is harder to maintain and does not take
    advantage of SV strengths (interfaces, packages,
    $clog2, assertions).
  Option C (rejected): Fully independent files with
    no enforced contract. Maximally flexible but
    creates a maintenance risk. Interface divergence
    is undetectable until system integration fails.
    Incompatible with the pssgen single-source model
    where either file must produce equivalent IR.
	
---

## D-028: All IP artifacts co-located under a single
          IP project directory

Decision: Every artifact belonging to an IP block —
source HDL, requirements, verification intent, register
map, documentation, generated testbench, compilation
scripts, and synthesis scripts — is located under a
single root directory named for the IP block.

The canonical structure is:

  ip/<block_name>/
    <block_name>.intent       — verification coverage intent
    <block_name>.req          — requirements and dispositions
    <block_name>_regmap.xlsx  — register map spreadsheet
    pssgen.toml               — pssgen project configuration
    DATASHEET.md              — IP data sheet (auto-generated)
    docs/                     — specification documents
    vhdl/                     — VHDL implementation
    sv/                       — SystemVerilog implementation
    tb/                       — generated testbench artifacts
    syntax/                   — DUT source syntax checks (ghdl, iverilog)
    synth/                    — synthesis scripts and reports

The pssgen.toml [output] section directs all generated
artifacts (PSS model, UVM testbench, RAL model, gap report,
data sheet) to the tb/ subdirectory rather than the
tool-default ./out directory.

Tool-default output directories (./out, ./build, etc.)
are not used for IP artifacts. They may exist temporarily
during development but are not committed and are not
the canonical location for any deliverable.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience managing IP libraries
across multiple programs and organisations where IP blocks
are handed off as complete, self-contained deliverables.
The failure mode of scattered artifacts is consistent and
predictable: the HDL is present, the testbench is missing,
the register map is in a shared drive no one can access,
and the synthesis results are in a colleague's home
directory. The receiving program starts from scratch.
Understanding that an IP block is only as portable as
its least accessible artifact — and that the natural
human instinct is to leave tool outputs in tool-default
locations — requires deliberate policy rather than
convention. Direct experience with DO-254 IP reuse
packages where the checklist item "all artifacts present
and accessible" is routinely the longest to close.

Why AI could not have made this decision alone:
An AI tool generating HDL naturally uses its own output
directory. The insight that generated artifacts should
travel with the IP rather than with the tool requires
understanding how IP is actually transferred between
programs and organisations — as a directory, a zip
file, or a git submodule — and that the recipient has
no access to the generating tool's working directory.
It also requires experience with the specific failure
mode of tool-scattered artifacts in program handoff
situations. An AI optimizing for simplicity would
use tool defaults. An AI optimizing for the IP library
use case puts everything in one place.

Alternatives considered:
  Option A (chosen): Single IP root directory. All
    artifacts co-located. pssgen.toml [output] overrides
    tool default. tb/, syntax/, synth/ subdirectories
    separate generated from hand-authored content.
    Self-contained — the directory is the deliverable.
  Option B (rejected): Tool-default output directories.
    ./out for pssgen, Vivado project directory elsewhere,
    scripts in repo root. Simpler for initial development.
    Breaks IP portability — artifacts scattered across
    the repo and tool working directories. A git clone
    does not produce a usable IP package without running
    all tools in sequence.
  Option C (rejected): Flat IP directory with no
    subdirectories. All files at the same level.
    Portable but becomes unnavigable beyond a handful
    of files. A fully implemented IP block with docs,
    HDL, testbench, synthesis reports, and scripts
    easily exceeds 30 files. Flat structure makes
    the distinction between hand-authored and generated
    content invisible.

---

## D-029: Testbench script organization under
          tb/scripts/<tool>/

Decision: Simulator-specific scripts that execute the
UVM testbench are located under tb/scripts/<tool>/
where <tool> is the lowercase simulator name. Each
tool directory is self-contained — it contains
everything needed to run the testbench on that
simulator without modifying any other directory.

Current and planned tool directories:

  tb/scripts/vivado/    — XSIM via Vivado batch mode
  tb/scripts/questa/    — Questa (future)
  tb/scripts/icarus/    — Icarus + UVM library (future)
  tb/scripts/modelsim/  — Modelsim (future)

Simulation compilation (xvlog, vlog, iverilog+UVM),
elaboration, and simulation are an indivisible
per-tool flow. All three steps live together in
tb/scripts/<tool>/ because separating them would
mean tool-specific knowledge leaking into multiple
locations. Each tool directory owns its complete
compile → elaborate → simulate sequence.

The syntax/ directory at the IP root is distinct
from tb/scripts/. syntax/ contains only DUT source
syntax checks (ghdl -a for VHDL, iverilog -t null
for SV). These require no UVM library and no
simulator license. They run on every commit as a
pre-commit gate. UVM testbench syntax is verified
by the full simulation flow in tb/scripts/<tool>/,
not by the pre-commit hook.

The utils/ directory at the IP root is reserved for
utilities shared across tool targets — Python helpers,
constraint generators, common shell functions. It
remains empty until a genuine shared utility exists.
Creating it empty with a README establishes the
location without creating noise.

The UVM testbench itself (tb/*.sv) is simulator-
agnostic. The tool-specific scripts in tb/scripts/
adapt it to each simulator's invocation model. This
separation means a new simulator target is added by
creating a new tb/scripts/<tool>/ directory without
touching the testbench source files.

pssgen generates tb/scripts/vivado/build.tcl as the
primary simulation target. Additional script targets
may be added as pssgen emission targets in future
phases. EDA Playground is identified as a long-term
target because it enables zero-install browser-based
simulation, which lowers the barrier for IP evaluation
and is consistent with pssgen's open-access mission.

Author: S. Belvin, BelTech Systems LLC

Domain knowledge required: Experience managing IP
verification environments across programs with
different simulator licenses. The per-tool directory
structure reflects the real constraint that different
teams have different simulation tools and a single
IP package needs to work with all of them without
modification. The distinction between source syntax
checks (syntax/) and simulation runs (tb/scripts/)
reflects experience with CI pipelines where syntax
checks run on every commit but full simulation runs
are gated — they require licenses and take time.
Understanding EDA Playground as a viable simulation
target requires awareness of the open-source FPGA
verification ecosystem and the market of engineers
who cannot justify simulator licenses for evaluation.

Why AI could not have made this decision alone:
The tb/scripts/<tool>/ structure reflects a specific
professional judgment about the granularity of tool
isolation. An AI might use a flat scripts/ directory
or put tool scripts alongside the testbench source.
The separation of DUT syntax checks (syntax/) from
simulation runs (tb/scripts/) reflects operational
experience with CI systems where these two activities
have different cost, frequency, and license requirements. The EDA Playground
identification reflects awareness of the open-source
FPGA community that is not captured in standard
training data about EDA workflows.

Alternatives considered:
  Option A (chosen): tb/scripts/<tool>/ per simulator.
    Testbench source is simulator-agnostic. Tool scripts
    are isolated. New simulators added without touching
    existing structure. syntax/ is separate for
    license-free DUT syntax checks.
  Option B (rejected): Single build script with
    tool selection flags. build.sh --tool vivado.
    Simpler for one tool. Becomes complex as tools
    multiply. Mixes simulator-specific logic.
    Harder to maintain when tool invocations diverge.
  Option C (rejected): Tool scripts alongside
    testbench source in tb/. Flat structure obscures
    which files are hand-authored versus tool-specific.
    Makes it harder to identify what needs updating
    when a simulator version changes.
---

## D-030: ModelSim as a named simulator target

Decision: ModelSim is recognised as a fourth named
simulator target alongside the three in D-015
(vivado, questa, icarus). It has its own directory:
tb/scripts/modelsim/ in every IP block.

Author: S. Belvin, BelTech Systems LLC

Rationale: ModelSim is the OEM simulation engine
bundled by three major FPGA vendors under different
product names:
  - ModelSim-Intel FPGA Edition (Quartus Lite/Prime)
  - ModelSim-Lattice Edition (Diamond, Radiant)
  - ModelSim-Microchip Edition (Libero SoC)
  - Siemens ModelSim (standalone commercial)

All four share the same vlog/vsim invocation and
do-file syntax. Covering ModelSim as a named target
reaches engineers on Intel, Lattice, and Microchip
FPGA platforms without requiring a separate Questa
license. An engineer using Quartus Lite on an Intel
FPGA has ModelSim at no additional cost; without a
named ModelSim target, pssgen would be effectively
unusable for that significant portion of the FPGA
user base.

The key distinction between this decision and D-015
is operational: D-015 chose icarus as the open-source
option. ModelSim fills a different niche — it is the
zero-marginal-cost commercial simulator that ships
with every FPGA IDE regardless of vendor. Engineers
using these tools are not choosing a simulator;
ModelSim was chosen for them by their toolchain.

Domain knowledge required: Awareness that FPGA vendors
bundle specific versions of ModelSim/Questa under their
own product names and that the resulting user population
is substantial. Most engineers on Intel FPGA platforms
have ModelSim-Intel as their only available simulator.
This is not apparent from public EDA market data and
requires familiarity with the end-user toolchain
landscape across different FPGA ecosystems.

Why AI could not have made this decision alone:
Requires knowledge that ModelSim-Intel FPGA Edition,
ModelSim-Lattice Edition, and ModelSim-Microchip
Edition are the same simulator under vendor-specific
licenses, and that reaching these users requires
a single named target rather than three. Also requires
the judgment that this population is large enough to
justify a first-class target rather than deferral.

Relationship to D-015:
D-015 chose four closure script targets: vivado, questa,
icarus, none. D-030 adds modelsim as a fifth named
target for tb/scripts/ directories. The closure script
targets and tb/scripts/ targets are managed separately
— the former is a pssgen emission option, the latter
is the IP block directory structure.
