// =============================================================================
// COV-007  INT_STATUS each_bit_independently
//
// Linked requirements:
//   UART-INT-001, UART-INT-002, UART-INT-003, UART-INT-004, UART-INT-005, UART-INT-006, UART-INT-007, UART-INT-008, UART-REG-037, UART-REG-039, UART-REG-040, UART-VER-004
//
// Stimulus strategy:
//   Each of 8 interrupt sources set and cleared independently via directed stimulus; verify IRQ asserts and deasserts correctly for each bit.
//
// Boundary values:
//   Each of 8 bits: TIMEOUT, TX_THRESH, RX_THRESH, TX_EMPTY, RX_FULL, PARITY_ERR, FRAME_ERR, OVERRUN — set and W1C cleared independently
// =============================================================================

class seq_RCOV007_int_status_each_bit_independently extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV007_int_status_each_bit_independently)

    function new(string name = "seq_RCOV007_int_status_each_bit_independently");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV007_int_status_each_bit_independently: body not yet implemented — see VPR COV-007",
            UVM_MEDIUM)
    endtask

endclass