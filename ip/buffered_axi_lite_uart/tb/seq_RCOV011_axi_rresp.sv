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
        bit [31:0] rdata;
        // Valid read → RRESP=OKAY
        axi_read(32'h00000000, rdata, "CTRL");
        // Undefined offset 0x30 → RRESP=SLVERR (hits cp_resp SLVERR bin)
        axi_read(32'h00000030, rdata, "INVALID_ADDR");
    endtask

endclass