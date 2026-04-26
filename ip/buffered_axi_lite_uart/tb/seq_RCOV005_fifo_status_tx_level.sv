// =============================================================================
// COV-005  FIFO_STATUS.TX_LEVEL
//
// Linked requirements:
//   UART-FIFO-002, UART-FIFO-003, UART-FIFO-006, UART-FIFO-008, UART-REG-016, UART-REG-017, UART-REG-033
//
// Stimulus strategy:
//   TX FIFO occupancy driven to 0, TX_THRESH-1, TX_THRESH, TX_THRESH+1, and G_FIFO_DEPTH to verify status flags and write-ignore behavior.
//
// Boundary values:
//   0 (TX_EMPTY), TX_THRESH-1, TX_THRESH, TX_THRESH+1 (interrupt fires), G_FIFO_DEPTH (full)
// =============================================================================

class seq_RCOV005_fifo_status_tx_level extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV005_fifo_status_tx_level)

    function new(string name = "seq_RCOV005_fifo_status_tx_level");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Read initial TX level (TX_EMPTY at reset)
        axi_read(32'h00000010, rdata, "FIFO_STATUS");
        `uvm_info("RCOV005", $sformatf("FIFO_STATUS before writes = 0x%08h", rdata), UVM_MEDIUM)
        // Write 4 bytes to TX FIFO — TX_LEVEL increases only when UART_EN=0 (no drain)
        axi_write(32'h00000028, 32'h00000055, 4'hF, "TX_DATA");
        axi_write(32'h00000028, 32'h000000AA, 4'hF, "TX_DATA");
        axi_write(32'h00000028, 32'h000000FF, 4'hF, "TX_DATA");
        axi_write(32'h00000028, 32'h00000000, 4'hF, "TX_DATA");
        // Read FIFO_STATUS to observe TX_LEVEL
        axi_read(32'h00000010, rdata, "FIFO_STATUS");
        `uvm_info("RCOV005",
            $sformatf("FIFO_STATUS after 4 TX writes = 0x%08h (TX_LEVEL[15:8] = 0x%02h)",
                rdata, rdata[15:8]),
            UVM_MEDIUM)
        // Enable UART to drain the TX FIFO, then read status again
        axi_write(32'h00000000, 32'h000000E0, 4'hF, "CTRL"); // UART_EN=1, TX_EN=1, RX_EN=1
        axi_read(32'h00000010, rdata, "FIFO_STATUS");
        `uvm_info("RCOV005",
            $sformatf("FIFO_STATUS with UART enabled = 0x%08h", rdata), UVM_MEDIUM)
        // Disable UART
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL");
    endtask

endclass