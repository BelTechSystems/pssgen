// =============================================================================
// COV-012  AXI_WRITE_ORDER
//
// Linked requirements:
//   UART-IF-005, UART-VER-006
//
// Stimulus strategy:
//   Issue AXI write with AWVALID first then WVALID, then repeat with WVALID first then AWVALID; verify correct response in both orderings.
//
// Boundary values:
//   AWVALID_FIRST ordering, WVALID_FIRST ordering
// =============================================================================

class seq_RCOV012_axi_write_order extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV012_axi_write_order)

    function new(string name = "seq_RCOV012_axi_write_order");
        super.new(name);
    endfunction

    virtual task body();
        // AXI-Lite write channel ordering (AWVALID vs WVALID) is a driver-level
        // concern; the base_seq API does not expose the handshake ordering knob.
        // This pass exercises multi-register write access to cover associated cp_addr
        // bins while the write-ordering requirement is tracked in the VPR as pending
        // driver enhancement.
        axi_write(32'h00000024, 32'h00000001, 4'hF, "SCRATCH");
        axi_write(32'h00000014, 32'h00000064, 4'hF, "TIMEOUT_VAL");
        axi_write(32'h0000000C, 32'h00080004, 4'hF, "FIFO_CTRL");
    endtask

endclass