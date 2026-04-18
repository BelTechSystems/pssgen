// ================================================================
// File       : axi4_lite_if.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : AXI4-Lite interface bundle with master and monitor clocking blocks.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017
//
// Functional blocks:
//   Signals              : All AXI4-Lite channel signals
//   master_cb            : Clocking block for BFM driving
//   monitor_cb           : Clocking block for passive observation
//
// Portability    : Simulator-independent
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
// ================================================================

interface axi4_lite_if #(
    parameter int ADDR_WIDTH = 32,
    parameter int DATA_WIDTH = 32
)(
    input logic ACLK,
    input logic ARESETn
);
    import uvm_pkg::*;

    // ── Write address channel ────────────────────────────────────────────────
    logic                     AWVALID;
    logic                     AWREADY;
    logic [ADDR_WIDTH-1:0]    AWADDR;
    logic [2:0]               AWPROT;

    // ── Write data channel ───────────────────────────────────────────────────
    logic                     WVALID;
    logic                     WREADY;
    logic [DATA_WIDTH-1:0]    WDATA;
    logic [DATA_WIDTH/8-1:0]  WSTRB;

    // ── Write response channel ───────────────────────────────────────────────
    logic                     BVALID;
    logic                     BREADY;
    logic [1:0]               BRESP;

    // ── Read address channel ─────────────────────────────────────────────────
    logic                     ARVALID;
    logic                     ARREADY;
    logic [ADDR_WIDTH-1:0]    ARADDR;
    logic [2:0]               ARPROT;

    // ── Read data channel ────────────────────────────────────────────────────
    logic                     RVALID;
    logic                     RREADY;
    logic [DATA_WIDTH-1:0]    RDATA;
    logic [1:0]               RRESP;

    // ── Master clocking block — drives all master-side outputs ───────────────
    clocking master_cb @(posedge ACLK);
        default input #1step output #1;
        output AWVALID, AWADDR, AWPROT;
        output WVALID,  WDATA,  WSTRB;
        output BREADY;
        output ARVALID, ARADDR, ARPROT;
        output RREADY;
        input  AWREADY;
        input  WREADY;
        input  BVALID,  BRESP;
        input  ARREADY;
        input  RVALID,  RDATA, RRESP;
    endclocking

    // ── Monitor clocking block — samples all signals ─────────────────────────
    clocking monitor_cb @(posedge ACLK);
        default input #1step;
        input AWVALID, AWREADY, AWADDR, AWPROT;
        input WVALID,  WREADY,  WDATA,  WSTRB;
        input BVALID,  BREADY,  BRESP;
        input ARVALID, ARREADY, ARADDR, ARPROT;
        input RVALID,  RREADY,  RDATA,  RRESP;
    endclocking

    // ── Modports ─────────────────────────────────────────────────────────────
    modport master  (clocking master_cb,  input ACLK, ARESETn);
    modport monitor (clocking monitor_cb, input ACLK, ARESETn);

endinterface
