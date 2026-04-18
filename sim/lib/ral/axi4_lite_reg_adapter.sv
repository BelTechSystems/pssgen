// ================================================================
// File       : axi4_lite_reg_adapter.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : UVM RAL adapter — maps uvm_reg_bus_op to axi4_lite_seq_item
//              and back. Connects the RAL register model to the AXI-Lite bus.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Functional blocks:
//   reg2bus()            : uvm_reg_bus_op → axi4_lite_seq_item
//   bus2reg()            : axi4_lite_seq_item → uvm_reg_bus_op status
//
// Dependencies:
//   uvm_pkg, axi4_lite_seq_item
//
// Portability    : Simulator-independent
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
// ================================================================

class axi4_lite_reg_adapter extends uvm_reg_adapter;

    `uvm_object_utils(axi4_lite_reg_adapter)

    function new(string name = "axi4_lite_reg_adapter");
        super.new(name);
        supports_byte_enable = 0;
        provides_responses   = 0;
    endfunction

    // ── RAL → bus ─────────────────────────────────────────────────────────────
    virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw);
        axi4_lite_seq_item item;
        item = axi4_lite_seq_item::type_id::create("reg2bus_item");
        item.kind = (rw.kind == UVM_READ) ? axi4_lite_seq_item::READ
                                           : axi4_lite_seq_item::WRITE;
        item.addr = rw.addr;
        item.data = rw.data;
        item.strb = 4'hF;
        return item;
    endfunction

    // ── bus → RAL ─────────────────────────────────────────────────────────────
    virtual function void bus2reg(
        uvm_sequence_item bus_item,
        ref uvm_reg_bus_op rw
    );
        axi4_lite_seq_item item;
        if (!$cast(item, bus_item))
            `uvm_fatal("ADAPTER", "bus2reg: cannot cast to axi4_lite_seq_item")
        rw.kind   = (item.kind == axi4_lite_seq_item::READ) ? UVM_READ : UVM_WRITE;
        rw.addr   = item.addr;
        rw.data   = item.data;
        rw.status = (item.resp == 2'b00) ? UVM_IS_OK : UVM_NOT_OK;
    endfunction

endclass
