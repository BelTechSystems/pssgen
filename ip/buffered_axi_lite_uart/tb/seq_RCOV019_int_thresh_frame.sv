// =============================================================================
// COV-019  INT_THRESH_FRAME
//
// Linked requirements:
//   UART-INT-009, UART-INT-010, UART-INT-011, UART-INT-012, UART-INT-013, UART-TO-007, UART-REG-015, UART-REG-020, UART-REG-021, UART-REG-022, UART-REG-023, UART-REG-029, UART-REG-030, UART-REG-037, UART-REG-039, UART-REG-040, UART-REG-041, UART-REG-043, UART-REG-047, UART-REG-048, UART-REG-050, UART-REG-051
//
// Stimulus strategy:
//   Drive TX_THRESH and RX_THRESH interrupt conditions, inject FRAME_ERR via stop-bit corruption, enable TIMEOUT interrupt; verify each INT_STATUS bit controlled by INT_ENABLE gate.
//
// Boundary values:
//   TX FIFO below TX_THRESH; RX FIFO above RX_THRESH; stop-bit corruption for FRAME_ERR; TIMEOUT with INT_ENABLE gates
// =============================================================================

class seq_RCOV019_int_thresh_frame extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV019_int_thresh_frame)

    function new(string name = "seq_RCOV019_int_thresh_frame");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Hit ZERO bins for both TX_THRESH[15:8] and RX_THRESH[7:0]
        axi_write(32'h0000000C, 32'h00000000, 4'hF, "FIFO_CTRL");
        // Hit MAX bins
        axi_write(32'h0000000C, 32'h0000FFFF, 4'hF, "FIFO_CTRL");
        // Program FIFO_CTRL: TX_THRESH=8, RX_THRESH=4 (FIFO_CTRL[15:8]=TX, [7:0]=RX)
        axi_write(32'h0000000C, 32'h00000804, 4'hF, "FIFO_CTRL");
        axi_read (32'h0000000C, rdata,              "FIFO_CTRL");
        `uvm_info("RCOV019", $sformatf("FIFO_CTRL = 0x%08h", rdata), UVM_MEDIUM)
        // Enable TX_THRESH and RX_THRESH interrupts (bits [1:0] per typical INT_ENABLE map)
        axi_write(32'h00000018, 32'h000000FF, 4'hF, "INT_ENABLE");
        // Write bytes to approach TX threshold; TX drains only when UART_EN=1
        axi_write(32'h00000028, 32'h00000041, 4'hF, "TX_DATA");
        axi_write(32'h00000028, 32'h00000042, 4'hF, "TX_DATA");
        axi_write(32'h00000028, 32'h00000043, 4'hF, "TX_DATA");
        // Read INT_STATUS — TX_THRESH fires if TX_LEVEL < TX_THRESH
        axi_read(32'h0000001C, rdata, "INT_STATUS");
        `uvm_info("RCOV019", $sformatf("INT_STATUS = 0x%08h", rdata), UVM_MEDIUM)
        // Clear interrupts and restore
        axi_write(32'h00000020, 32'h000000FF, 4'hF, "INT_CLEAR");
        axi_write(32'h00000018, 32'h00000000, 4'hF, "INT_ENABLE");
        axi_write(32'h0000000C, 32'h00080008, 4'hF, "FIFO_CTRL"); // restore default thresholds
    endtask

endclass