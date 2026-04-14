// =============================================================================
// COV-011  AXI_RRESP
//
// Linked requirements:
//   UART-IF-007, UART-IF-009, UART-REG-001
//
// Stimulus strategy:
//   AXI read from valid register offset (OKAY expected) and from undefined offset 0x30 (SLVERR expected); capture RRESP each time.
//
// Boundary values:
//   Valid offset RRESP=OKAY, undefined offset 0x30 RRESP=SLVERR
// =============================================================================

class seq_RCOV011_axi_rresp extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV011_axi_rresp)

    function new(string name = "seq_RCOV011_axi_rresp");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV011_axi_rresp: body not yet implemented — see VPR COV-011",
            UVM_MEDIUM)
    endtask

endclass