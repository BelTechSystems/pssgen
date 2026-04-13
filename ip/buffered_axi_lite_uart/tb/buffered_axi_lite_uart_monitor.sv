class buffered_axi_lite_uart_monitor extends uvm_monitor;
    `uvm_component_utils(buffered_axi_lite_uart_monitor)

    virtual buffered_axi_lite_uart_if              vif;
    uvm_analysis_port #(buffered_axi_lite_uart_seq_item) ap;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        ap = new("ap", this);
        if (!uvm_config_db #(virtual buffered_axi_lite_uart_if)::get(
                this, "", "vif", vif))
            `uvm_fatal("NO_VIF",
                "buffered_axi_lite_uart_monitor: vif not found in config_db")
    endfunction

    task run_phase(uvm_phase phase);
        buffered_axi_lite_uart_seq_item item;
        // Latches for channel data — populated on handshake, used at response
        bit [7:0]  aw_addr_lat_s;
        bit [31:0] wd_data_lat_s;
        bit [3:0]  wd_strb_lat_s;
        bit [7:0]  ar_addr_lat_s;

        @(posedge vif.axi_aclk iff vif.axi_aresetn === 1'b1);

        forever begin
            @(posedge vif.axi_aclk);

            // Latch AW handshake address
            if (vif.s_axi_awvalid === 1'b1 && vif.s_axi_awready === 1'b1)
                aw_addr_lat_s = vif.s_axi_awaddr;

            // Latch W handshake data and strobe
            if (vif.s_axi_wvalid === 1'b1 && vif.s_axi_wready === 1'b1) begin
                wd_data_lat_s = vif.s_axi_wdata;
                wd_strb_lat_s = vif.s_axi_wstrb;
            end

            // Completed write: B handshake
            if (vif.s_axi_bvalid === 1'b1 && vif.s_axi_bready === 1'b1) begin
                item = buffered_axi_lite_uart_seq_item::type_id::create("mon_wr");
                item.cmd   = buffered_axi_lite_uart_seq_item::AXI_WRITE;
                item.addr  = {24'b0, aw_addr_lat_s};
                item.wdata = wd_data_lat_s;
                item.wstrb = wd_strb_lat_s;
                item.resp  = vif.s_axi_bresp;
                ap.write(item);
            end

            // Latch AR handshake address
            if (vif.s_axi_arvalid === 1'b1 && vif.s_axi_arready === 1'b1)
                ar_addr_lat_s = vif.s_axi_araddr;

            // Completed read: R handshake
            if (vif.s_axi_rvalid === 1'b1 && vif.s_axi_rready === 1'b1) begin
                item = buffered_axi_lite_uart_seq_item::type_id::create("mon_rd");
                item.cmd   = buffered_axi_lite_uart_seq_item::AXI_READ;
                item.addr  = {24'b0, ar_addr_lat_s};
                item.rdata = vif.s_axi_rdata;
                item.resp  = vif.s_axi_rresp;
                ap.write(item);
            end
        end
    endtask

endclass
