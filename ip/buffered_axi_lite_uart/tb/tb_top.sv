`timescale 1ns/1ps

module tb_top;

    import uvm_pkg::*;
    import buffered_axi_lite_uart_pkg::*;
    `include "uvm_macros.svh"

    // -------------------------------------------------------------------------
    // Clock / reset
    // -------------------------------------------------------------------------
    logic clk;

    // Interface instance
    buffered_axi_lite_uart_if intf(.clk(clk));

    // -------------------------------------------------------------------------
    // DUT
    // -------------------------------------------------------------------------
    // Mixed-language note:
    // If the DUT is VHDL, Vivado mixed-language elaboration will still allow
    // this style of instantiation as long as the VHDL entity name is
    // buffered_axi_lite_uart and it is compiled into the same simulation.
    buffered_axi_lite_uart dut (
        .axi_aclk      (intf.axi_aclk),
        .axi_aresetn   (intf.axi_aresetn),

        .s_axi_awvalid (intf.s_axi_awvalid),
        .s_axi_awready (intf.s_axi_awready),
        .s_axi_awaddr  (intf.s_axi_awaddr),
        .s_axi_awprot  (intf.s_axi_awprot),

        .s_axi_wvalid  (intf.s_axi_wvalid),
        .s_axi_wready  (intf.s_axi_wready),
        .s_axi_wdata   (intf.s_axi_wdata),
        .s_axi_wstrb   (intf.s_axi_wstrb),

        .s_axi_bvalid  (intf.s_axi_bvalid),
        .s_axi_bready  (intf.s_axi_bready),
        .s_axi_bresp   (intf.s_axi_bresp),

        .s_axi_arvalid (intf.s_axi_arvalid),
        .s_axi_arready (intf.s_axi_arready),
        .s_axi_araddr  (intf.s_axi_araddr),
        .s_axi_arprot  (intf.s_axi_arprot),

        .s_axi_rvalid  (intf.s_axi_rvalid),
        .s_axi_rready  (intf.s_axi_rready),
        .s_axi_rdata   (intf.s_axi_rdata),
        .s_axi_rresp   (intf.s_axi_rresp),

        .uart_tx       (intf.uart_tx),
        .uart_rx       (intf.uart_rx),
        .irq           (intf.irq)
    );

    // -------------------------------------------------------------------------
    // Clock generation
    // -------------------------------------------------------------------------
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;  // 100 MHz
    end

    // -------------------------------------------------------------------------
    // Default signal initialization
    // -------------------------------------------------------------------------
    initial begin
        // Hook the interface clock/reset to the local TB clock
        intf.axi_aclk    = 1'b0;
        intf.axi_aresetn = 1'b0;

        // AXI write address channel
        intf.s_axi_awvalid = 1'b0;
        intf.s_axi_awaddr  = '0;
        intf.s_axi_awprot  = '0;

        // AXI write data channel
        intf.s_axi_wvalid  = 1'b0;
        intf.s_axi_wdata   = '0;
        intf.s_axi_wstrb   = '0;

        // AXI write response channel
        intf.s_axi_bready  = 1'b0;

        // AXI read address channel
        intf.s_axi_arvalid = 1'b0;
        intf.s_axi_araddr  = '0;
        intf.s_axi_arprot  = '0;

        // AXI read data channel
        intf.s_axi_rready  = 1'b0;

        // UART
        intf.uart_rx       = 1'b1;  // UART idle high

        // irq is DUT output, so do not drive it
    end

    // -------------------------------------------------------------------------
    // Drive the DUT clock and reset through the interface
    // -------------------------------------------------------------------------
    always_comb begin
        intf.axi_aclk = clk;
    end

    initial begin
        // Hold reset active for a few cycles
        intf.axi_aresetn = 1'b0;
        repeat (10) @(posedge clk);
        intf.axi_aresetn = 1'b1;
    end

    // -------------------------------------------------------------------------
    // Optional UART loopback for bring-up
    // -------------------------------------------------------------------------
    // Uncomment this if you want a simple external loopback path.
    // Be careful: if the DUT also supports internal loopback, do not enable both.
    //
    // always_comb begin
    //     intf.uart_rx = intf.uart_tx;
    // end

    // -------------------------------------------------------------------------
    // UVM configuration and test start
    // -------------------------------------------------------------------------
    initial begin
        uvm_config_db#(virtual buffered_axi_lite_uart_if)::set(
            null,
            "*",
            "vif",
            intf
        );

        run_test();
    end

    // -------------------------------------------------------------------------
    // Optional waveform dump
    // -------------------------------------------------------------------------
    initial begin
        $dumpfile("tb_top.vcd");
        $dumpvars(0, tb_top);
    end

endmodule