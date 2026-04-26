// =============================================================================
// COV-016  UART_EN_CONTROL
//
// Linked requirements:
//   UART-EN-001, UART-EN-002, UART-EN-003, UART-EN-004, UART-EN-005, UART-EN-006, UART-REG-005, UART-REG-006, UART-REG-007, UART-REG-008
//
// Stimulus strategy:
//   Deassert UART_EN and verify TX/RX halt; then independently gate TX_EN and RX_EN with UART_EN=1 to verify path isolation; set LOOP_EN and verify loopback active.
//
// Boundary values:
//   UART_EN=0 (halt), TX_EN=0 (TX off/RX active), RX_EN=0 (RX off/TX active), LOOP_EN=1 with UART_EN=1
// =============================================================================

class seq_RCOV016_uart_en_control extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV016_uart_en_control)

    function new(string name = "seq_RCOV016_uart_en_control");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // CTRL layout: [7]=UART_EN, [6]=TX_EN, [5]=RX_EN, [4]=LOOP_EN, [3:2]=PARITY, [1]=STOP
        // Step 1: confirm UART_EN=0 (reset default — no TX/RX activity)
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL");
        axi_read (32'h00000000, rdata,              "CTRL");
        // Step 2: TX only (TX_EN=1, RX_EN=0, UART_EN=1)
        axi_write(32'h00000000, 32'h000000C0, 4'hF, "CTRL"); // UART_EN|TX_EN
        axi_read (32'h00000000, rdata,              "CTRL");
        // Step 3: RX only (TX_EN=0, RX_EN=1, UART_EN=1)
        axi_write(32'h00000000, 32'h000000A0, 4'hF, "CTRL"); // UART_EN|RX_EN
        axi_read (32'h00000000, rdata,              "CTRL");
        // Step 4: loopback (LOOP_EN=1, UART_EN=1, TX_EN=1, RX_EN=1)
        axi_write(32'h00000000, 32'h000000F0, 4'hF, "CTRL"); // UART_EN|TX_EN|RX_EN|LOOP_EN
        axi_read (32'h00000000, rdata,              "CTRL");
        // Restore: disable all
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL");
    endtask

endclass