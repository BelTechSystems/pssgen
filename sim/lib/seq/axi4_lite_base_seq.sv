// ================================================================
// File       : axi4_lite_base_seq.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : Base RAL sequence providing reg_write, reg_read, and
//              reg_poll helpers. All BALU COV sequences extend this class.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Functional blocks:
//   reg_write()          : RAL write with UVM_IS_OK check
//   reg_read()           : RAL read with UVM_IS_OK check; returns value
//   reg_poll()           : Repeated RAL reads until mask/expected match
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

class axi4_lite_base_seq extends uvm_reg_sequence #(uvm_sequence);

    `uvm_object_utils(axi4_lite_base_seq)

    // Typed register model handle — populated in pre_body() from config_db.
    balu_reg_model              reg_model;
    // Virtual interface handle — populated in pre_body() from config_db.
    virtual axi4_lite_if        vif;

    function new(string name = "axi4_lite_base_seq");
        super.new(name);
    endfunction

    task pre_body();
        if (!uvm_config_db #(balu_reg_model)::get(
                null, get_full_name(), "reg_model", reg_model))
            `uvm_fatal(get_name(), "pre_body: balu_reg_model not in config_db")
        if (!uvm_config_db #(virtual axi4_lite_if)::get(
                null, get_full_name(), "vif", vif))
            `uvm_fatal(get_name(), "pre_body: virtual axi4_lite_if not in config_db")
    endtask

    // ── Write one register and assert UVM_IS_OK ───────────────────────────────
    virtual task reg_write(
        input uvm_reg         reg_h,
        input uvm_reg_data_t  value
    );
        uvm_status_e status;
        reg_h.write(status, value, UVM_FRONTDOOR, .parent(this));
        if (status != UVM_IS_OK)
            `uvm_error(get_name(),
                $sformatf("RAL write failed for %s", reg_h.get_name()))
    endtask

    // ── Read one register and return its value ────────────────────────────────
    virtual task reg_read(
        input  uvm_reg         reg_h,
        output uvm_reg_data_t  value
    );
        uvm_status_e status;
        reg_h.read(status, value, UVM_FRONTDOOR, .parent(this));
        if (status != UVM_IS_OK)
            `uvm_error(get_name(),
                $sformatf("RAL read failed for %s", reg_h.get_name()))
    endtask

    // ── Poll a register until (rdata & mask) == expected, or timeout ──────────
    virtual task reg_poll(
        input uvm_reg         reg_h,
        input uvm_reg_data_t  mask,
        input uvm_reg_data_t  expected,
        input int unsigned    timeout_cycles
    );
        uvm_reg_data_t rdata;
        int unsigned   count = 0;
        do begin
            reg_read(reg_h, rdata);
            if ((rdata & mask) == expected) return;
            count++;
        end while (count < timeout_cycles);
        `uvm_error(get_name(),
            $sformatf("reg_poll timeout on %s after %0d cycles",
                      reg_h.get_name(), timeout_cycles))
    endtask

endclass
