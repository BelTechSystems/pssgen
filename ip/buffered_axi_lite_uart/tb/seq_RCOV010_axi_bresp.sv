// =============================================================================
// COV-010  AXI_BRESP
//
// Linked requirements:
//   UART-IF-006, UART-IF-008, UART-REG-001
//
// Stimulus strategy:
//   AXI write to valid register offset (OKAY expected) and to undefined offset 0x30 (SLVERR expected); capture BRESP each time.
//
// Boundary values:
//   Valid offset BRESP=OKAY, undefined offset 0x30 BRESP=SLVERR
// =============================================================================

class seq_RCOV010_axi_bresp extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV010_axi_bresp)

    function new(string name = "seq_RCOV010_axi_bresp");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV010_axi_bresp: body not yet implemented — see VPR COV-010",
            UVM_MEDIUM)
    endtask

endclass