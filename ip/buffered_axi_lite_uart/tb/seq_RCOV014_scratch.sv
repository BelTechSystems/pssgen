// =============================================================================
// COV-014  SCRATCH
//
// Linked requirements:
//   UART-REG-044, UART-REG-045, UART-REG-046, UART-VER-003
//
// Stimulus strategy:
//   Write walking-ones (0x00000001 through 0x80000000), all-ones (0xFFFFFFFF), and all-zeros (0x00000000) to SCRATCH; read back and verify each value.
//
// Boundary values:
//   0x00000001..0x80000000 (walking ones), 0x000000FF, 0xFFFFFFFF (all-ones), 0x00000000 (all-zeros)
// =============================================================================

class seq_RCOV014_scratch extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV014_scratch)

    function new(string name = "seq_RCOV014_scratch");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV014_scratch: body not yet implemented — see VPR COV-014",
            UVM_MEDIUM)
    endtask

endclass