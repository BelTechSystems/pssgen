// =============================================================================
// COV-002  CTRL.PARITY
//
// Linked requirements:
//   UART-FF-005, UART-FF-006, UART-FF-007, UART-FF-008, UART-FF-009, UART-REG-009, UART-VER-009
//
// Stimulus strategy:
//   All four parity modes (00/01/10/11) exercised independently in LOOP_EN loopback; inject parity error bit for odd and even modes.
//
// Boundary values:
//   2'b00 (none), 2'b01 (odd+error inject), 2'b10 (even+error inject), 2'b11 (mark)
// =============================================================================

class seq_RCOV002_ctrl_parity extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV002_ctrl_parity)

    function new(string name = "seq_RCOV002_ctrl_parity");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV002_ctrl_parity: body not yet implemented — see VPR COV-002",
            UVM_MEDIUM)
    endtask

endclass