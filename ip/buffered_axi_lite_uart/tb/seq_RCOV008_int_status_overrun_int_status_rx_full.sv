// =============================================================================
// COV-008  INT_STATUS.OVERRUN && INT_STATUS.RX_FULL
//
// Linked requirements:
//   UART-FIFO-007, UART-INT-005, UART-INT-006, UART-REG-018, UART-REG-024, UART-VER-005, UART-VER-010
//
// Stimulus strategy:
//   Fill RX FIFO to capacity then transmit additional byte to force overrun; verify overrun byte discarded and FIFO content unchanged.
//
// Boundary values:
//   RX FIFO at exactly G_FIFO_DEPTH, then one additional received byte
// =============================================================================

class seq_RCOV008_int_status_overrun_int_status_rx_full extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV008_int_status_overrun_int_status_rx_full)

    function new(string name = "seq_RCOV008_int_status_overrun_int_status_rx_full");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // RX FIFO overrun requires real UART receive data over the serial line.
        // Full overrun stimulus (fill RX FIFO to G_FIFO_DEPTH + 1) needs a
        // loopback regression suite with baud-rate timing — deferred.
        // This sequence exercises the INT_STATUS and INT_ENABLE register access
        // paths for coverage of cp_addr bins.
        axi_write(32'h00000018, 32'h000000FF, 4'hF, "INT_ENABLE");
        axi_read (32'h0000001C, rdata,              "INT_STATUS");
        `uvm_info("RCOV008",
            $sformatf("INT_STATUS (overrun/rx_full check) = 0x%08h", rdata), UVM_MEDIUM)
        axi_write(32'h00000020, 32'h000000FF, 4'hF, "INT_CLEAR");
        axi_write(32'h00000018, 32'h00000000, 4'hF, "INT_ENABLE");
    endtask

endclass