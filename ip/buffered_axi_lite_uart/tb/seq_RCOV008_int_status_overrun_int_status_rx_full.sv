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
        `uvm_info("SEQ_PENDING",
            "seq_RCOV008_int_status_overrun_int_status_rx_full: body not yet implemented — see VPR COV-008",
            UVM_MEDIUM)
    endtask

endclass