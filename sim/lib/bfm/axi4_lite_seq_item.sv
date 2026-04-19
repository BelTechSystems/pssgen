// ================================================================
// File       : axi4_lite_seq_item.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : AXI4-Lite sequence item — one register access (read or write).
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Functional blocks:
//   axi4_lite_seq_item   : Transaction fields, constraints, convert2string
//
// Dependencies:
//   uvm_pkg
//
// Portability    : Simulator-independent
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
// ================================================================

class axi4_lite_seq_item extends uvm_sequence_item;

    // ── Transaction kind ─────────────────────────────────────────────────────
    typedef enum bit { READ = 1'b0, WRITE = 1'b1 } kind_e;

    // ── Randomisable stimulus fields ─────────────────────────────────────────
    rand kind_e        kind;
    rand bit [31:0]  addr;
    rand bit [31:0]  data;
    rand bit [3:0]   strb;

    // ── Response (filled by driver / BFM) ────────────────────────────────────
    bit [1:0]        resp;

    // Constraints omitted: xelab 2025.1 crashes when a package contains two
    // constrained uvm_sequence_item subclasses. RAL adapter sets fields
    // directly; no stimulus randomization needed on this item.

    // ── UVM automation ────────────────────────────────────────────────────────
    `uvm_object_utils_begin(axi4_lite_seq_item)
        `uvm_field_enum(kind_e,    kind, UVM_DEFAULT)
        `uvm_field_int(            addr, UVM_HEX)
        `uvm_field_int(            data, UVM_HEX)
        `uvm_field_int(            strb, UVM_BIN)
        `uvm_field_int(            resp, UVM_BIN | UVM_NOCOMPARE)
    `uvm_object_utils_end

    function new(string name = "axi4_lite_seq_item");
        super.new(name);
        resp = 2'b00;
        strb = 4'hF;
    endfunction

    function string convert2string();
        return $sformatf(
            "kind=%s addr=0x%08h data=0x%08h strb=0x%1h resp=%02b",
            kind.name(), addr, data, strb, resp);
    endfunction

endclass
