// ================================================================
// File       : axi4_lite_master_bfm.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : Reusable AXI4-Lite master BFM — drives write/read transactions
//              onto an axi4_lite_if virtual interface.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Functional blocks:
//   write()              : Drive AW/W/B channels; capture BRESP
//   read()               : Drive AR/R channels; capture RDATA and RRESP
//
// Dependencies:
//   uvm_pkg, axi4_lite_if, axi4_lite_seq_item
//
// Portability    : Vivado/Questa xsim-compatible
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
// ================================================================

class axi4_lite_master_bfm #(
    int ADDR_WIDTH = 32,
    int DATA_WIDTH = 32
) extends uvm_component;

    `uvm_component_param_utils(axi4_lite_master_bfm #(ADDR_WIDTH, DATA_WIDTH))

    // ── Virtual interface handle ──────────────────────────────────────────────
    virtual axi4_lite_if #(ADDR_WIDTH, DATA_WIDTH) vif;

    // ── Analysis port for observed transactions ───────────────────────────────
    uvm_analysis_port #(axi4_lite_seq_item) ap;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
        if (!uvm_config_db #(virtual axi4_lite_if #(ADDR_WIDTH, DATA_WIDTH))::get(
                this, "", "axi_vif", vif))
            `uvm_fatal("NO_VIF", "axi4_lite_master_bfm: axi_vif not in config_db")
    endfunction

    // ── Reset guard — stall until ARESETn is deasserted ──────────────────────
    local task _wait_reset();
        if (!vif.ARESETn) begin
            @(posedge vif.ACLK iff vif.ARESETn === 1'b1);
        end
    endtask

    // ── Write transaction ─────────────────────────────────────────────────────
    // Drives AWVALID/AWADDR and WVALID/WDATA/WSTRB simultaneously.
    // Waits for AWREADY and WREADY independently (may arrive in any order).
    // Then captures BRESP on BVALID.
    task write(
        input  logic [ADDR_WIDTH-1:0] addr,
        input  logic [DATA_WIDTH-1:0] data,
        output logic [1:0]            bresp
    );
        axi4_lite_seq_item obs;
        logic aw_done, w_done;

        _wait_reset();

        aw_done = 1'b0;
        w_done  = 1'b0;

        // Assert AW and W channels simultaneously on the next clock edge
        @(posedge vif.ACLK);
        vif.AWVALID <= 1'b1;
        vif.AWADDR  <= addr;
        vif.AWPROT  <= 3'b000;
        vif.WVALID  <= 1'b1;
        vif.WDATA   <= data;
        vif.WSTRB   <= {(DATA_WIDTH/8){1'b1}};

        // De-assert each channel as its READY arrives
        while (!aw_done || !w_done) begin
            @(posedge vif.ACLK);
            if (vif.AWREADY && !aw_done) begin
                vif.AWVALID <= 1'b0;
                vif.AWADDR  <= '0;
                aw_done = 1'b1;
            end
            if (vif.WREADY && !w_done) begin
                vif.WVALID <= 1'b0;
                vif.WDATA  <= '0;
                vif.WSTRB  <= '0;
                w_done = 1'b1;
            end
        end

        // Assert BREADY and wait for BVALID
        vif.BREADY <= 1'b1;
        @(posedge vif.ACLK iff vif.BVALID === 1'b1);
        bresp = vif.BRESP;
        @(posedge vif.ACLK);
        vif.BREADY <= 1'b0;

        // Publish observation
        obs = axi4_lite_seq_item::type_id::create("wr_obs");
        obs.kind = axi4_lite_seq_item::WRITE;
        obs.addr = addr;
        obs.data = data;
        obs.resp = bresp;
        ap.write(obs);
    endtask

    // ── Read transaction ──────────────────────────────────────────────────────
    // Drives ARVALID/ARADDR, waits for ARREADY.
    // Then asserts RREADY and captures RDATA/RRESP on RVALID.
    task read(
        input  logic [ADDR_WIDTH-1:0] addr,
        output logic [DATA_WIDTH-1:0] rdata,
        output logic [1:0]            rresp
    );
        axi4_lite_seq_item obs;

        _wait_reset();

        // AR channel
        @(posedge vif.ACLK);
        vif.ARVALID <= 1'b1;
        vif.ARADDR  <= addr;
        vif.ARPROT  <= 3'b000;
        @(posedge vif.ACLK iff vif.ARREADY === 1'b1);
        vif.ARVALID <= 1'b0;
        vif.ARADDR  <= '0;

        // R channel
        vif.RREADY <= 1'b1;
        @(posedge vif.ACLK iff vif.RVALID === 1'b1);
        rdata = vif.RDATA;
        rresp = vif.RRESP;
        @(posedge vif.ACLK);
        vif.RREADY <= 1'b0;

        // Publish observation
        obs = axi4_lite_seq_item::type_id::create("rd_obs");
        obs.kind = axi4_lite_seq_item::READ;
        obs.addr = addr;
        obs.data = rdata;
        obs.resp = rresp;
        ap.write(obs);
    endtask

endclass
