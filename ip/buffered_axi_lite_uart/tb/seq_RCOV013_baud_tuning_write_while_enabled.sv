// =============================================================================
// COV-013  BAUD_TUNING_WRITE_WHILE_ENABLED
//
// Linked requirements:
//   UART-REG-028, UART-VER-007
//
// Stimulus strategy:
//   Assert UART_EN, write a new value to BAUD_TUNING, read back and verify original value unchanged; confirms silent-ignore while enabled.
//
// Boundary values:
//   UART_EN=1, write new value, readback must equal original value
// =============================================================================

class seq_RCOV013_baud_tuning_write_while_enabled extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV013_baud_tuning_write_while_enabled)

    function new(string name = "seq_RCOV013_baud_tuning_write_while_enabled");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV013_baud_tuning_write_while_enabled: body not yet implemented — see VPR COV-013",
            UVM_MEDIUM)
    endtask

endclass