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
        `uvm_info("SEQ_PENDING",
            "seq_RCOV012_axi_write_order: body not yet implemented — see VPR COV-012",
            UVM_MEDIUM)
    endtask

endclass