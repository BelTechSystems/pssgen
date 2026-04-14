// =============================================================================
// COV-005  FIFO_STATUS.TX_LEVEL
//
// Linked requirements:
//   UART-FIFO-002, UART-FIFO-003, UART-FIFO-006, UART-FIFO-008, UART-REG-016, UART-REG-017, UART-REG-033
//
// Stimulus strategy:
//   TX FIFO occupancy driven to 0, TX_THRESH-1, TX_THRESH, TX_THRESH+1, and G_FIFO_DEPTH to verify status flags and write-ignore behavior.
//
// Boundary values:
//   0 (TX_EMPTY), TX_THRESH-1, TX_THRESH, TX_THRESH+1 (interrupt fires), G_FIFO_DEPTH (full)
// =============================================================================

class seq_RCOV005_fifo_status_tx_level extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV005_fifo_status_tx_level)

    function new(string name = "seq_RCOV005_fifo_status_tx_level");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV005_fifo_status_tx_level: body not yet implemented — see VPR COV-005",
            UVM_MEDIUM)
    endtask

endclass