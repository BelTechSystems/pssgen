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
    typedef enum logic { READ = 1'b0, WRITE = 1'b1 } kind_e;

    // ── Randomisable stimulus fields ─────────────────────────────────────────
    rand kind_e        kind;
    rand logic [31:0]  addr;
    rand logic [31:0]  data;
    rand logic [3:0]   strb;

    // ── Response (filled by driver / BFM) ────────────────────────────────────
    logic [1:0]        resp;

    // ── Constraints ──────────────────────────────────────────────────────────
    // AXI-Lite registers are 32-bit aligned
    constraint c_addr_align { addr[1:0] == 2'b00; }

    // BALU register map: offsets 0x00 to 0x34
    constraint c_addr_balu  { addr inside {[32'h0000_0000 : 32'h0000_0034]}; }

    // Full-word strobe default for writes; zero for reads
    constraint c_strb_by_kind {
        if (kind == WRITE) strb == 4'hF;
        else               strb == 4'h0;
    }

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
