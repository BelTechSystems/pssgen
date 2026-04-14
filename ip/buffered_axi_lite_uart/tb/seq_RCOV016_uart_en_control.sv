// =============================================================================
// COV-016  UART_EN_CONTROL
//
// Linked requirements:
//   UART-EN-001, UART-EN-002, UART-EN-003, UART-EN-004, UART-EN-005, UART-EN-006, UART-REG-005, UART-REG-006, UART-REG-007, UART-REG-008
//
// Stimulus strategy:
//   Deassert UART_EN and verify TX/RX halt; then independently gate TX_EN and RX_EN with UART_EN=1 to verify path isolation; set LOOP_EN and verify loopback active.
//
// Boundary values:
//   UART_EN=0 (halt), TX_EN=0 (TX off/RX active), RX_EN=0 (RX off/TX active), LOOP_EN=1 with UART_EN=1
// =============================================================================

class seq_RCOV016_uart_en_control extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV016_uart_en_control)

    function new(string name = "seq_RCOV016_uart_en_control");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV016_uart_en_control: body not yet implemented — see VPR COV-016",
            UVM_MEDIUM)
    endtask

endclass