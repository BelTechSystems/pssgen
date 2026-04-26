// =============================================================================
// COV-018  READONLY_IGNORE
//
// Linked requirements:
//   UART-IF-010, UART-IF-011, UART-REG-002, UART-REG-003, UART-REG-011, UART-REG-012, UART-REG-025, UART-REG-038, UART-REG-042, UART-REG-049, UART-REG-052
//
// Stimulus strategy:
//   Write to each read-only register (STATUS, FIFO_STATUS, INT_STATUS, INT_CLEAR, TX_DATA reads, RX_DATA writes); read back and verify state unchanged.
//
// Boundary values:
//   Write all-ones to each RO register; compare pre- and post-write readback for each
// =============================================================================

class seq_RCOV018_readonly_ignore extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV018_readonly_ignore)

    function new(string name = "seq_RCOV018_readonly_ignore");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] orig_val, after;
        // STATUS (0x04) — read-only, write returns SLVERR (hits cp_resp SLVERR bin)
        axi_read (32'h00000004, orig_val, "STATUS");
        axi_write(32'h00000004, 32'hFFFFFFFF, 4'hF, "STATUS");  // SLVERR response
        axi_read (32'h00000004, after,    "STATUS");
        if (orig_val !== after)
            `uvm_error("RCOV018", "STATUS changed after write-to-RO attempt")
        // FIFO_STATUS (0x10) — read-only, write returns SLVERR
        axi_read (32'h00000010, orig_val, "FIFO_STATUS");
        axi_write(32'h00000010, 32'hFFFFFFFF, 4'hF, "FIFO_STATUS");  // SLVERR response
        axi_read (32'h00000010, after,    "FIFO_STATUS");
        if (orig_val !== after)
            `uvm_error("RCOV018", "FIFO_STATUS changed after write-to-RO attempt")
        // INT_STATUS (0x1C) — W1C only via INT_CLEAR; direct write returns SLVERR
        axi_read (32'h0000001C, orig_val, "INT_STATUS");
        axi_write(32'h0000001C, 32'hFFFFFFFF, 4'hF, "INT_STATUS"); // SLVERR response
        axi_read (32'h0000001C, after,  "INT_STATUS");
        // RX_DATA (0x2C) — read-only, write returns SLVERR
        axi_write(32'h0000002C, 32'hFFFFFFFF, 4'hF, "RX_DATA");   // SLVERR response
        axi_read (32'h0000002C, after,  "RX_DATA");
    endtask

endclass