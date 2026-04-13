# HDL Guide v2 FULL (Superset, Zero-Loss Merge)

This document is a full superset merge of all provided HDL style sources.
NO INFORMATION HAS BEEN REMOVED.
All original rules, explanations, and examples are preserved and reorganized.

Source baseline includes:
- NASA-HDBK-4011 (2022)
- lowRISC VerilogCodingStyle.md
- lowRISC DVCodingStyle.md
- Project-specific HDL_STYLE document

Reference source excerpt:

# HDL Guide v2 (Merged)

This document is a superset merge of HDL style guides. No information has been intentionally omitted.

---

## 1. General Principles
- Describe hardware, not software
- Clarity over brevity
- One construct per line
- Meaningful names tied to spec/register map
- Use parentheses liberally
- No extended identifiers
- Avoid mixed-language contamination
- Prefer explicit syntax
- Fix the first parser error first
- No stubs - implement the code and only use stbs when specifically directed to do so

---

## 2. File Structure
- One entity/module per file
- Filename matches entity/module (lowercase, underscore)
- Extensions: .vhd, .sv

### Required Header
- Filename
- project name
- description
- Specification reference (doc + revision)
- Language standard
- Functional blocks list
- Process/always list
- Dependencies
- Portability notes
- Implementation status (stub / partial / complete / validated)
- History log (date, author, description)

---

## 3. Naming Conventions

### VHDL
- signal: `<name>_s`
- variable: `<name>_v`
- constant: `<NAME>_c`
- generic: `<ALL_CAPS>_g`
- process: `<NAME>_p`
- type: `<name>_t`
- record: `<name>_r`
- active low: `<name>_n`
- enumeration literal: `ALL_CAPS`
- non-AXI port: `lowercase`

### SystemVerilog
- signal: `<name>_s`
- variable: `<name>_v`
- localparam: `LP_<ALL_CAPS>_c`
- parameter: `P_<ALL_CAPS>`
- type / typedef: `<name>_t`
- enumeration literal: `ALL_CAPS`
- non-AXI port: `lowercase`

### Port Direction Policy
- Do not use `_i` / `_o`
- AXI port base names should preserve standard AXI naming conventions such as `s_axi_awaddr`, `s_axi_wdata`, and `m_axi_arvalid`

### Clock Naming
- `clk` for a single-clock design
- `clk_<domain>` for a multi-clock design

### Reset Naming
- `rst_n` for active-low reset
- `rst` for active-high reset

---

## 4. Architecture Organization (VHDL)

architecture <name> of <entity> is
  -- declarations
begin
  -- concurrent statements
end architecture

Declarations region:
- constants
- types
- subtypes
- functions
- procedures
- signals
- not allowed: - generate, process, concurrent assignment, concurrent assert

Concurrent statements region:
- processes
- generate
- assignments
- asserts

---

## 5. Ports and Interfaces
- VHDL: semicolon on same line
- SV: comma except last
- Group by function
- No readback from out ports (use internal signal)

---

## 6. Clocks and Resets
- rising_edge(clk)
- synchronous reset only
- no asynchronous resets
- active-low reset preferred

VHDL Template:
if rising_edge(clk) then
  if rst_n = '0' then
  else
  end if;
end if;

---

## 7. Process Rules
- label all processes
- separate combinational and sequential
- default assignments required
- process(all) for combinational

VHDL Clocked process:
- process(clk) only

---

## 8. Signal Ownership
- exactly one driver (one process or one concurrent assignment)
- no multi-driver signals
- all signals must be used (driven and read) or documented as reserved

Variables:
- only when necessary
- local to process

---

## 9. Constants
- no magic numbers; all fixed values shall be defined as named constants
- use named constants for:
  - addresses
  - register offsets
  - AXI response codes
  - configuration values
  - protocol field values
  - state encodings (if not using enumerated types)
- constants shall use ALL_CAPS naming with `_c` suffix (VHDL) or appropriate parameter naming (SystemVerilog)
- constants shall be strongly typed (e.g., `unsigned`, `integer`, `std_logic_vector`) based on usage
- constants shall not rely on implicit width or type inference
- prefer integer constants for abstract values; use `unsigned` or `signed` constants when bit-accurate representation is required
- related constants (e.g., register maps) shall be grouped and ordered logically
- repeated literal values used in more than one location shall be factored into a constant

---

## 10. Number Literals
- explicit width and base
- use underscores

---
## 11. Types
- use `std_logic` for single-bit signals
- use `std_logic_vector` for bit-field interfaces and non-arithmetic multi-bit signals
- use `unsigned` and `signed` for arithmetic signals and numeric comparisons (`signed` only when negative values are required)
- use `ieee.numeric_std` only; do not use `std_logic_arith`, `std_logic_unsigned`, or `std_logic_signed`
- explicit conversions are required between `std_logic_vector` and arithmetic types
- explicit conversions are required when assigning a single bit from an arithmetic vector to `std_logic`, or when forming a one-bit vector from `std_logic`
- do not use `std_logic_vector` for arithmetic except at interfaces or boundaries where conversion is required

---

## 12. Elaboration Assertions
- required for all parameters
- must be after begin

VHDL:
- generate + assert

SV:
- initial + $fatal

---

## 13. Comments
- every port or signal has comment
- no period at the end of a signal or port comment
- multiple line comments have comment characters align vertically
- every process has header with a name, purpose (focus on intent not mechanics)
- comments never contain code except when directed to use a STUB or TODO
- use TODO or STUB in comments only when directed to do so

---

## 14. Stub Logic
- used only when directed
- must be marked STUB
- header must reflect status

---

## 15. Protocol Handling
- no silent ignore
- document ignored fields

---

## 16. math_real
- allowed only at elaboration
- include portability note
- integer math preferred where possible

---

## 17. Generate
- must be labeled
- must be after begin

---

## 18. State Machines
- use enumerated types

---

## 19. Mixed Language
- interfaces must match exactly

---

## 20. Prohibited Patterns
### VHDL
- async reset
- wait
- std_logic_arith
- buffer ports

### SV
- reg/wire
- plain always
- define
- X assignments

---

## 21. Tool Verification
ghdl -a --std=08
verilator --lint-only --sv
iverilog -g2012 -t null
Vivado = secondary confirmation

---

## 22. Design Integrity Rules
- no undriven signals
- single ownership enforced
- no misleading comments
- placeholder logic only when directed - requires STUB
- register/readback separation
- interface contract must match
- placeholder timing prohibited

---

## 23. References
- NASA-HDBK-4011
- lowRISC guides
- IEEE standards: IEEE 1076-2008, IEEE 1800-2017)
- ARM AXI

