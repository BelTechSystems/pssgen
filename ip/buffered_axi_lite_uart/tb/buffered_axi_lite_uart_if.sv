interface buffered_axi_lite_uart_if (
    input logic axi_aclk
);
    // AXI-Lite slave port signals — mirror buffered_axi_lite_uart module ports
    logic        axi_aresetn;
    logic        s_axi_awvalid;
    logic        s_axi_awready;
    logic [7:0]  s_axi_awaddr;
    logic [2:0]  s_axi_awprot;
    logic        s_axi_wvalid;
    logic        s_axi_wready;
    logic [31:0] s_axi_wdata;
    logic [3:0]  s_axi_wstrb;
    logic        s_axi_bvalid;
    logic        s_axi_bready;
    logic [1:0]  s_axi_bresp;
    logic        s_axi_arvalid;
    logic        s_axi_arready;
    logic [7:0]  s_axi_araddr;
    logic [2:0]  s_axi_arprot;
    logic        s_axi_rvalid;
    logic        s_axi_rready;
    logic [31:0] s_axi_rdata;
    logic [1:0]  s_axi_rresp;
    logic        uart_tx;
    logic        uart_rx;
    logic        irq;
endinterface
