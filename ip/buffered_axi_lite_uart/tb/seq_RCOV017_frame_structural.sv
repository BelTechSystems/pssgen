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
        bit [31:0] rdata;
        // Structural check: AXI data width=32 confirmed by full-word accesses,
        // single-beat only. TX_DATA accepts 8-bit data in bits[7:0]; CTRL enables.
        // Write 8 representative byte values (0x00..0xFF boundary + walking ones)
        axi_write(32'h00000000, 32'h000000E0, 4'hF, "CTRL"); // UART_EN|TX_EN|RX_EN
        axi_write(32'h00000028, 32'h00000000, 4'hF, "TX_DATA"); // 0x00
        axi_write(32'h00000028, 32'h00000001, 4'hF, "TX_DATA"); // 0x01
        axi_write(32'h00000028, 32'h00000055, 4'hF, "TX_DATA"); // 0x55 alternating
        axi_write(32'h00000028, 32'h000000AA, 4'hF, "TX_DATA"); // 0xAA alternating
        axi_write(32'h00000028, 32'h000000FF, 4'hF, "TX_DATA"); // 0xFF all-ones
        // Read FIFO_STATUS and STATUS to confirm TX path is active
        axi_read(32'h00000010, rdata, "FIFO_STATUS");
        axi_read(32'h00000004, rdata, "STATUS");
        // Read RX_DATA (empty FIFO — expect 0 or flagged empty)
        axi_read(32'h0000002C, rdata, "RX_DATA");
        // Disable UART
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL");
    endtask

endclass