// =============================================================================
// COV-009  INT_STATUS.TIMEOUT && INT_STATUS.RX_THRESH
//
// Linked requirements:
//   UART-TO-005, UART-INT-002, UART-INT-008, UART-REG-014
//
// Stimulus strategy:
//   Set TIMEOUT_VAL non-zero, fill RX FIFO above RX_THRESH, then idle until timeout fires; verify both INT_STATUS.TIMEOUT and INT_STATUS.RX_THRESH set simultaneously.
//
// Boundary values:
//   RX FIFO > RX_THRESH (threshold set), then idle until timeout fires while threshold remains set
// =============================================================================

class seq_RCOV009_int_status_timeout_int_status_rx_thresh extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV009_int_status_timeout_int_status_rx_thresh)

    function new(string name = "seq_RCOV009_int_status_timeout_int_status_rx_thresh");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV009_int_status_timeout_int_status_rx_thresh: body not yet implemented — see VPR COV-009",
            UVM_MEDIUM)
    endtask

endclass