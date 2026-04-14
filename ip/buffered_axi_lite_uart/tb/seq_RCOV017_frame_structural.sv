// =============================================================================
// COV-017  FRAME_STRUCTURAL
//
// Linked requirements:
//   UART-FF-001, UART-FIFO-001, UART-IF-001, UART-IF-002, UART-IF-003, UART-IF-004, UART-IF-012, UART-IF-013, UART-IF-014, UART-PAR-001, UART-PAR-002, UART-PAR-009, UART-REG-032, UART-REG-033, UART-REG-034
//
// Stimulus strategy:
//   Structural inspection: verify 8-bit data frames transmitted and received, AXI data width=32, address width sufficient, single-beat transactions only.
//
// Boundary values:
//   8-bit frames; FIFO depth=G_FIFO_DEPTH; AXI data width=32; no burst transactions
// =============================================================================

class seq_RCOV017_frame_structural extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV017_frame_structural)

    function new(string name = "seq_RCOV017_frame_structural");
        super.new(name);
    endfunction

    virtual task body();
        `uvm_info("SEQ_PENDING",
            "seq_RCOV017_frame_structural: body not yet implemented — see VPR COV-017",
            UVM_MEDIUM)
    endtask

endclass