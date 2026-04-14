// =============================================================================
// COV-018  READONLY_IGNORE
//
// Linked requirements:
//   UART-IF-010, UART-IF-011, UART-REG-002, UART-REG-003, UART-REG-011, UART-REG-012, UART-REG-025, UART-REG-038, UART-REG-042, UART-REG-049, UART-REG-052
//
// Stimulus strategy:
//   Write to each read-only register (STATUS, FIFO_STATUS, INT_STATUS, INT_CLEAR, TX_DATA reads, RX_DATA writes); read back and verify state unchanged.
//
// Boundary values:
//   Write all-ones to each RO register; compare pre- and post-write readback for each
// =============================================================================

class seq_RCOV018_readonly_ignore extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV018_readonly_ignore)

    function new(string name = "seq_RCOV018_readonly_ignore");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV018_readonly_ignore: body not yet implemented — see VPR COV-018",
            UVM_MEDIUM)
    endtask

endclass