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

    // BR family: baud rate divisor value coverage
    covergroup baud_rate_cg;
        cp_baud_write: coverpoint item_s.wdata
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h08) {
            bins ZERO        = {32'h00000000};
            bins MIN         = {32'h00000001};
            bins BAUD_9600   = {32'h00064A9D};
            bins BAUD_115200 = {32'h004B7F5A};
            bins MAX         = {32'hFFFFFFFF};
            bins OTHER       = default;
        }
    endgroup

    // EN family: UART enable/disable transitions
    covergroup uart_enable_cg;
        cp_uart_en: coverpoint item_s.wdata[7]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h00) {
            bins DISABLED = {1'b0};
            bins ENABLED  = {1'b1};
        }
    endgroup

    // PAR family: parity mode configuration
    covergroup parity_cg;
        cp_parity_mode: coverpoint item_s.wdata[3:2]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h00) {
            bins NONE = {2'b00};
            bins EVEN = {2'b01};
            bins ODD  = {2'b10};
        }
    endgroup

    // PAR/VER family: stop bit configuration
    covergroup stop_bits_cg;
        cp_stop_bits: coverpoint item_s.wdata[5:4]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h00) {
            bins ONE      = {2'b00};
            bins ONE_HALF = {2'b01};
            bins TWO      = {2'b10};
        }
    endgroup

    // FIFO family: TX and RX FIFO threshold configuration
    covergroup fifo_threshold_cg;
        cp_tx_thresh: coverpoint item_s.wdata[15:8]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h0C) {
            bins ZERO  = {8'h00};
            bins HALF  = {8'h08};
            bins MAX   = {8'hFF};
            bins OTHER = default;
        }
        cp_rx_thresh: coverpoint item_s.wdata[7:0]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h0C) {
            bins ZERO  = {8'h00};
            bins HALF  = {8'h08};
            bins MAX   = {8'hFF};
            bins OTHER = default;
        }
    endgroup

    // TO family: timeout counter value coverage
    covergroup timeout_cg;
        cp_timeout_val: coverpoint item_s.wdata[15:0]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h14) {
            bins ZERO  = {16'h0000};
            bins MIN   = {16'h0001};
            bins MID   = {16'h0064};
            bins MAX   = {16'hFFFF};
            bins OTHER = default;
        }
    endgroup

    // INT family: interrupt enable register coverage
    covergroup interrupt_enable_cg;
        cp_int_enable: coverpoint item_s.wdata[7:0]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h18) {
            bins ALL_OFF = {8'h00};
            bins ALL_ON  = {8'hFF};
            bins OTHER   = default;
        }
    endgroup

    // INT family: interrupt clear register coverage
    covergroup interrupt_clear_cg;
        cp_int_clear: coverpoint item_s.wdata[7:0]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_WRITE &&
                 item_s.addr[7:0] == 8'h20) {
            bins CLEAR_NONE = {8'h00};
            bins CLEAR_ALL  = {8'hFF};
            bins OTHER      = default;
        }
    endgroup

    // RST family: reset value verification via read-back
    covergroup reset_values_cg;
        cp_ctrl_reset: coverpoint item_s.rdata[7:0]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_READ &&
                 item_s.addr[7:0] == 8'h00) {
            bins RESET_VALUE = {8'h00};
            bins OTHER       = default;
        }
    endgroup

    // FF family: RO register read coverage
    covergroup ro_access_cg;
        cp_ro_read: coverpoint item_s.addr[7:0]
            iff (item_s.cmd == buffered_axi_lite_uart_seq_item::AXI_READ) {
            bins STATUS      = {8'h04};
            bins FIFO_STATUS = {8'h10};
            bins INT_STATUS  = {8'h1C};
            bins RX_DATA     = {8'h2C};
        }
    endgroup

    // IF family: SLVERR response on write-to-RO registers
    covergroup error_response_cg;
        cp_slverr_addr: coverpoint item_s.addr[7:0]
            iff (item_s.resp == 2'b10) {
            bins STATUS      = {8'h04};
            bins FIFO_STATUS = {8'h10};
            bins INT_STATUS  = {8'h1C};
            bins RX_DATA     = {8'h2C};
            bins UNKNOWN     = default;
        }
    endgroup

    function new(string name, uvm_component parent);
        super.new(name, parent);
        // Vivado requires embedded covergroups to be instantiated in new(),
        // not in build_phase (VRFC 10-8922).
        axi_transaction_cg  = new();
        baud_rate_cg        = new();
        uart_enable_cg      = new();
        parity_cg           = new();
        stop_bits_cg        = new();
        fifo_threshold_cg   = new();
        timeout_cg          = new();
        interrupt_enable_cg = new();
        interrupt_clear_cg  = new();
        reset_values_cg     = new();
        ro_access_cg        = new();
        error_response_cg   = new();
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
    endfunction

    virtual function void write(buffered_axi_lite_uart_seq_item t);
        item_s = t;
        axi_transaction_cg.sample();
        baud_rate_cg.sample();
        uart_enable_cg.sample();
        parity_cg.sample();
        stop_bits_cg.sample();
        fifo_threshold_cg.sample();
        timeout_cg.sample();
        interrupt_enable_cg.sample();
        interrupt_clear_cg.sample();
        reset_values_cg.sample();
        ro_access_cg.sample();
        error_response_cg.sample();
    endfunction

    function void report_phase(uvm_phase phase);
        real overall_avg_v;
        overall_avg_v = (axi_transaction_cg.get_coverage()  +
                         baud_rate_cg.get_coverage()         +
                         uart_enable_cg.get_coverage()       +
                         parity_cg.get_coverage()            +
                         stop_bits_cg.get_coverage()         +
                         fifo_threshold_cg.get_coverage()    +
                         timeout_cg.get_coverage()           +
                         interrupt_enable_cg.get_coverage()  +
                         interrupt_clear_cg.get_coverage()   +
                         reset_values_cg.get_coverage()      +
                         ro_access_cg.get_coverage()         +
                         error_response_cg.get_coverage()) / 12.0;
        `uvm_info("COV", $sformatf(
            "axi_transaction_cg:   %.1f%%\nbaud_rate_cg:         %.1f%%\nuart_enable_cg:       %.1f%%\nparity_cg:            %.1f%%\nstop_bits_cg:         %.1f%%\nfifo_threshold_cg:    %.1f%%\ntimeout_cg:           %.1f%%\ninterrupt_enable_cg:  %.1f%%\ninterrupt_clear_cg:   %.1f%%\nreset_values_cg:      %.1f%%\nro_access_cg:         %.1f%%\nerror_response_cg:    %.1f%%\nOverall functional:   %.1f%%",
            axi_transaction_cg.get_coverage(),
            baud_rate_cg.get_coverage(),
            uart_enable_cg.get_coverage(),
            parity_cg.get_coverage(),
            stop_bits_cg.get_coverage(),
            fifo_threshold_cg.get_coverage(),
            timeout_cg.get_coverage(),
            interrupt_enable_cg.get_coverage(),
            interrupt_clear_cg.get_coverage(),
            reset_values_cg.get_coverage(),
            ro_access_cg.get_coverage(),
            error_response_cg.get_coverage(),
            overall_avg_v),
            UVM_MEDIUM)
    endfunction

endclass
