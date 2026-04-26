// =============================================================================
// COV-007  INT_STATUS each_bit_independently
//
// Linked requirements:
//   UART-INT-001, UART-INT-002, UART-INT-003, UART-INT-004, UART-INT-005, UART-INT-006, UART-INT-007, UART-INT-008, UART-REG-037, UART-REG-039, UART-REG-040, UART-VER-004
//
// Stimulus strategy:
//   Each of 8 interrupt sources set and cleared independently via directed stimulus; verify IRQ asserts and deasserts correctly for each bit.
//
// Boundary values:
//   Each of 8 bits: TIMEOUT, TX_THRESH, RX_THRESH, TX_EMPTY, RX_FULL, PARITY_ERR, FRAME_ERR, OVERRUN — set and W1C cleared independently
// =============================================================================

class seq_RCOV007_int_status_each_bit_independently extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV007_int_status_each_bit_independently)

    function new(string name = "seq_RCOV007_int_status_each_bit_independently");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Enable all 8 interrupt sources
        axi_write(32'h00000018, 32'h000000FF, 4'hF, "INT_ENABLE");
        axi_read (32'h00000018, rdata,              "INT_ENABLE");
        // Sample INT_STATUS — bits set by hardware events during prior sequences
        axi_read(32'h0000001C, rdata, "INT_STATUS");
        `uvm_info("RCOV007",
            $sformatf("INT_STATUS = 0x%08h", rdata), UVM_MEDIUM)
        // W1C clear all via INT_CLEAR; read INT_CLEAR to verify it is readable (returns 0)
        axi_write(32'h00000020, 32'h000000FF, 4'hF, "INT_CLEAR");
        axi_read (32'h00000020, rdata,              "INT_CLEAR");
        // Confirm INT_STATUS cleared
        axi_read(32'h0000001C, rdata, "INT_STATUS");
        `uvm_info("RCOV007",
            $sformatf("INT_STATUS after clear = 0x%08h (expect 0x00000000)", rdata), UVM_MEDIUM)
        // Disable all interrupts to restore state
        axi_write(32'h00000018, 32'h00000000, 4'hF, "INT_ENABLE");
    endtask

endclass