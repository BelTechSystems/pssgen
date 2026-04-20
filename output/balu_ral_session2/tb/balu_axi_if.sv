// ==============================================================
// File       : balu_axi_if.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ==============================================================
// Brief      : Non-parameterized AXI4-Lite interface for BALU TB.
//              Fixed 32-bit address and data widths.
//              Non-parameterized to avoid xelab 2025.1 crash with
//              virtual parameterized interfaces as uvm_config_db types.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017
//
// History:
//   2026-04-19  pssgen  RAL Session 3: non-param workaround for xelab 2025.1
// ==============================================================
interface balu_axi_if (
    input logic ACLK,
    input logic ARESETn
);
    // Driven by sequences via reset_dut(); ANDed with tb_top rst_n before DUT.
    logic ARESETn_seq = 1'b1;
    // Write address channel
    logic        AWVALID;
    logic        AWREADY;
    logic [31:0] AWADDR;
    logic [2:0]  AWPROT;

    // Write data channel
    logic        WVALID;
    logic        WREADY;
    logic [31:0] WDATA;
    logic [3:0]  WSTRB;

    // Write response channel
    logic        BVALID;
    logic        BREADY;
    logic [1:0]  BRESP;

    // Read address channel
    logic        ARVALID;
    logic        ARREADY;
    logic [31:0] ARADDR;
    logic [2:0]  ARPROT;

    // Read data channel
    logic        RVALID;
    logic        RREADY;
    logic [31:0] RDATA;
    logic [1:0]  RRESP;

endinterface
