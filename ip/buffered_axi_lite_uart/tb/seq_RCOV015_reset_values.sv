// =============================================================================
// COV-015  RESET_VALUES
//
// Linked requirements:
//   UART-RST-001, UART-RST-002, UART-RST-003, UART-RST-004, UART-RST-005, UART-RST-006, UART-REG-004, UART-REG-013, UART-REG-031, UART-REG-036, UART-REG-046, UART-PAR-007, UART-PAR-008, UART-VER-002
//
// Stimulus strategy:
//   Assert then deassert reset; read all 12 registers and compare each field to the reset value specified in Table 8-x.
//
// Boundary values:
//   12 register reset values per spec Table 8-x
// =============================================================================

class seq_RCOV015_reset_values extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV015_reset_values)

    function new(string name = "seq_RCOV015_reset_values");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV015_reset_values: body not yet implemented — see VPR COV-015",
            UVM_MEDIUM)
    endtask

endclass