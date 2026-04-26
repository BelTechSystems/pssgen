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
        // Valid write → BRESP=OKAY
        axi_write(32'h00000024, 32'hA5A5A5A5, 4'hF, "SCRATCH");
        // Undefined offset 0x30 → BRESP=SLVERR (hits cp_resp SLVERR bin)
        axi_write(32'h00000030, 32'hDEADBEEF, 4'hF, "INVALID_ADDR");
    endtask

endclass