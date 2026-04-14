// =============================================================================
// COV-006  TIMEOUT_VAL
//
// Linked requirements:
//   UART-TO-001, UART-TO-002, UART-TO-003, UART-TO-004, UART-TO-005, UART-TO-006, UART-REG-035, UART-REG-036, UART-PAR-006, UART-VER-008
//
// Stimulus strategy:
//   TIMEOUT_VAL set to 0x0000, 0x0001, G_TIMEOUT_DEFAULT, 0xFFFE, and 0xFFFF; idle receiver until timeout fires for each non-zero value.
//
// Boundary values:
//   0x0000 (disabled), 0x0001 (minimum active), G_TIMEOUT_DEFAULT (reset), 0xFFFE, 0xFFFF (maximum)
// =============================================================================

class seq_RCOV006_timeout_val extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV006_timeout_val)

    function new(string name = "seq_RCOV006_timeout_val");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV006_timeout_val: body not yet implemented — see VPR COV-006",
            UVM_MEDIUM)
    endtask

endclass