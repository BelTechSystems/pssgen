// =============================================================================
// COV-003  CTRL.STOP_BITS
//
// Linked requirements:
//   UART-FF-002, UART-FF-003, UART-FF-004, UART-REG-010
//
// Stimulus strategy:
//   Both stop bit configurations (1 and 2 stop bits) exercised in LOOP_EN loopback with frame integrity check.
//
// Boundary values:
//   1'b0 (1 stop bit), 1'b1 (2 stop bits)
// =============================================================================

class seq_RCOV003_ctrl_stop_bits extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV003_ctrl_stop_bits)

    function new(string name = "seq_RCOV003_ctrl_stop_bits");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV003_ctrl_stop_bits: body not yet implemented — see VPR COV-003",
            UVM_MEDIUM)
    endtask

endclass