// ================================================================
// File       : bfm_pkg.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : Package wrapping the reusable AXI-Lite BFM library.
//              Compile sim/lib/bfm/axi4_lite_if.sv first (interface),
//              then compile this package.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Include order (dependency-ordered):
//   axi4_lite_seq_item   → no internal deps
//   axi4_lite_master_bfm → depends on seq_item
//   axi4_lite_reg_adapter→ depends on seq_item
//   balu_reg_model       → no BFM deps (pure RAL)
//   axi4_lite_base_seq   → depends on UVM RAL
//
// Portability    : Simulator-independent
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
// ================================================================

package bfm_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    `include "sim/lib/bfm/axi4_lite_seq_item.sv"
    // axi4_lite_master_bfm omitted: parameterized class crashes xelab 2025.1
    `include "sim/lib/ral/axi4_lite_reg_adapter.sv"
    // axi4_lite_predictor omitted: parameterized class with user type crashes xelab 2025.1
    `include "sim/lib/ral/balu_reg_model.sv"
    // axi4_lite_base_seq omitted: uvm_reg_sequence parameterization crashes xelab 2025.1

endpackage
