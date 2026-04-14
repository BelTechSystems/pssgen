// =============================================================================
// COV-019  INT_THRESH_FRAME
//
// Linked requirements:
//   UART-INT-009, UART-INT-010, UART-INT-011, UART-INT-012, UART-INT-013, UART-TO-007, UART-REG-015, UART-REG-020, UART-REG-021, UART-REG-022, UART-REG-023, UART-REG-029, UART-REG-030, UART-REG-037, UART-REG-039, UART-REG-040, UART-REG-041, UART-REG-043, UART-REG-047, UART-REG-048, UART-REG-050, UART-REG-051
//
// Stimulus strategy:
//   Drive TX_THRESH and RX_THRESH interrupt conditions, inject FRAME_ERR via stop-bit corruption, enable TIMEOUT interrupt; verify each INT_STATUS bit controlled by INT_ENABLE gate.
//
// Boundary values:
//   TX FIFO below TX_THRESH; RX FIFO above RX_THRESH; stop-bit corruption for FRAME_ERR; TIMEOUT with INT_ENABLE gates
// =============================================================================

class seq_RCOV019_int_thresh_frame extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV019_int_thresh_frame)

    function new(string name = "seq_RCOV019_int_thresh_frame");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV019_int_thresh_frame: body not yet implemented — see VPR COV-019",
            UVM_MEDIUM)
    endtask

endclass