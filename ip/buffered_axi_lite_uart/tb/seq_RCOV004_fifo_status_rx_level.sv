// =============================================================================
// COV-004  FIFO_STATUS.RX_LEVEL
//
// Linked requirements:
//   UART-FIFO-004, UART-FIFO-005, UART-FIFO-007, UART-FIFO-009, UART-REG-019, UART-REG-034
//
// Stimulus strategy:
//   RX FIFO occupancy driven to 0, RX_THRESH-1, RX_THRESH, RX_THRESH+1, and G_FIFO_DEPTH to verify status flags and overrun discard.
//
// Boundary values:
//   0 (RX_EMPTY), RX_THRESH-1, RX_THRESH, RX_THRESH+1 (interrupt fires), G_FIFO_DEPTH (full/overrun)
// =============================================================================

class seq_RCOV004_fifo_status_rx_level extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV004_fifo_status_rx_level)

    function new(string name = "seq_RCOV004_fifo_status_rx_level");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV004_fifo_status_rx_level: body not yet implemented — see VPR COV-004",
            UVM_MEDIUM)
    endtask

endclass