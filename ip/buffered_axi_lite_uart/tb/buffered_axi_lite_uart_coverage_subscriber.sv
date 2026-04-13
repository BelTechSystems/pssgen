class buffered_axi_lite_uart_coverage_subscriber extends
    uvm_subscriber #(buffered_axi_lite_uart_seq_item);

    `uvm_component_utils(buffered_axi_lite_uart_coverage_subscriber)

    // Current transaction — updated before each sample() call.
    buffered_axi_lite_uart_seq_item item_s;

    covergroup axi_transaction_cg;

        // Confirms bidirectional bus traffic: both READ and WRITE must be hit.
        cp_cmd: coverpoint item_s.cmd {
            bins AXI_WRITE = {buffered_axi_lite_uart_seq_item::AXI_WRITE};
            bins AXI_READ  = {buffered_axi_lite_uart_seq_item::AXI_READ};
        }

        // One named bin per register — confirms each register was accessed.
        cp_addr: coverpoint item_s.addr[7:0] {
            bins CTRL        = {8'h00};
            bins STATUS      = {8'h04};
            bins BAUD_TUNING = {8'h08};
            bins FIFO_CTRL   = {8'h0C};
            bins FIFO_STATUS = {8'h10};
            bins TIMEOUT_VAL = {8'h14};
            bins INT_ENABLE  = {8'h18};
            bins INT_STATUS  = {8'h1C};
            bins INT_CLEAR   = {8'h20};
            bins SCRATCH     = {8'h24};
            bins TX_DATA     = {8'h28};
            bins RX_DATA     = {8'h2C};
        }

        // Unhit SLVERR bin is informative — shows no error responses seen.
        cp_resp: coverpoint item_s.resp {
            bins OKAY   = {2'b00};
            bins SLVERR = {2'b10};
        }

        // Cross: confirms every register was both read and written where
        // access type permits. Unhit bins for RO/WO registers are expected.
        cp_cmd_x_addr: cross cp_cmd, cp_addr;

    endgroup

    function new(string name, uvm_component parent);
        super.new(name, parent);
        // Vivado requires embedded covergroups to be instantiated in new(),
        // not in build_phase (VRFC 10-8922).
        axi_transaction_cg = new();
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
    endfunction

    virtual function void write(buffered_axi_lite_uart_seq_item t);
        item_s = t;
        axi_transaction_cg.sample();
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("COV",
            $sformatf("axi_transaction_cg coverage: %.1f%%",
                axi_transaction_cg.get_coverage()),
            UVM_MEDIUM)
    endfunction

endclass
