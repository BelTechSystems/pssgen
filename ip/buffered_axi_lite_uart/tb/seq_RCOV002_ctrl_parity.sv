// =============================================================================
// COV-002  CTRL.PARITY
//
// Linked requirements:
//   UART-FF-005, UART-FF-006, UART-FF-007, UART-FF-008, UART-FF-009, UART-REG-009, UART-VER-009
//
// Stimulus strategy:
//   All four parity modes (00/01/10/11) exercised independently in LOOP_EN loopback; inject parity error bit for odd and even modes.
//
// Boundary values:
//   2'b00 (none), 2'b01 (odd+error inject), 2'b10 (even+error inject), 2'b11 (mark)
// =============================================================================

class seq_RCOV002_ctrl_parity extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV002_ctrl_parity)

    function new(string name = "seq_RCOV002_ctrl_parity");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // CTRL[3:2] = parity mode: 00=none, 01=odd, 10=even, 11=mark
        // UART_EN=0 (reset default) — no restriction on CTRL writes
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL"); // parity=none
        axi_read (32'h00000000, rdata,              "CTRL");
        axi_write(32'h00000000, 32'h00000004, 4'hF, "CTRL"); // parity=odd  (bits[3:2]=01)
        axi_read (32'h00000000, rdata,              "CTRL");
        axi_write(32'h00000000, 32'h00000008, 4'hF, "CTRL"); // parity=even (bits[3:2]=10)
        axi_read (32'h00000000, rdata,              "CTRL");
        axi_write(32'h00000000, 32'h0000000C, 4'hF, "CTRL"); // parity=mark (bits[3:2]=11)
        axi_read (32'h00000000, rdata,              "CTRL");
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL"); // restore: disable all
    endtask

endclass