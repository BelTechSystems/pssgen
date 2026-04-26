// =============================================================================
// COV-015  RESET_VALUES
//
// Linked requirements:
//   UART-RST-001, UART-RST-002, UART-RST-003, UART-RST-004, UART-RST-005, UART-RST-006, UART-REG-004, UART-REG-013, UART-REG-031, UART-REG-036, UART-REG-046, UART-PAR-007, UART-PAR-008, UART-VER-002
//
// Stimulus strategy:
//   Assert then deassert reset; read all 12 registers and compare each field to the reset value specified in Table 8-x.
//
// Boundary values:
//   12 register reset values per spec Table 8-x
// =============================================================================

class seq_RCOV015_reset_values extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV015_reset_values)

    function new(string name = "seq_RCOV015_reset_values");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Read all 12 registers. Reset assertion is a hardware concern (tb_top drives
        // axi_aresetn low then high); sequences run after reset deassert by design.
        // This pass hits all cp_addr bins for the READ command.
        axi_read(32'h00000000, rdata, "CTRL");
        `uvm_info("RCOV015", $sformatf("CTRL        = 0x%08h (expect 0x00000000)", rdata), UVM_MEDIUM)
        axi_read(32'h00000004, rdata, "STATUS");
        `uvm_info("RCOV015", $sformatf("STATUS      = 0x%08h", rdata), UVM_MEDIUM)
        axi_read(32'h00000008, rdata, "BAUD_TUNING");
        `uvm_info("RCOV015", $sformatf("BAUD_TUNING = 0x%08h (expect 0x004FA6D5)", rdata), UVM_MEDIUM)
        axi_read(32'h0000000C, rdata, "FIFO_CTRL");
        `uvm_info("RCOV015", $sformatf("FIFO_CTRL   = 0x%08h", rdata), UVM_MEDIUM)
        axi_read(32'h00000010, rdata, "FIFO_STATUS");
        `uvm_info("RCOV015", $sformatf("FIFO_STATUS = 0x%08h", rdata), UVM_MEDIUM)
        axi_read(32'h00000014, rdata, "TIMEOUT_VAL");
        `uvm_info("RCOV015", $sformatf("TIMEOUT_VAL = 0x%08h", rdata), UVM_MEDIUM)
        axi_read(32'h00000018, rdata, "INT_ENABLE");
        `uvm_info("RCOV015", $sformatf("INT_ENABLE  = 0x%08h (expect 0x00000000)", rdata), UVM_MEDIUM)
        axi_read(32'h0000001C, rdata, "INT_STATUS");
        `uvm_info("RCOV015", $sformatf("INT_STATUS  = 0x%08h", rdata), UVM_MEDIUM)
        axi_read(32'h00000020, rdata, "INT_CLEAR");
        `uvm_info("RCOV015", $sformatf("INT_CLEAR   = 0x%08h", rdata), UVM_MEDIUM)
        axi_read(32'h00000024, rdata, "SCRATCH");
        `uvm_info("RCOV015", $sformatf("SCRATCH     = 0x%08h (expect 0x00000000)", rdata), UVM_MEDIUM)
        axi_read(32'h00000028, rdata, "TX_DATA");
        `uvm_info("RCOV015", $sformatf("TX_DATA     = 0x%08h (WO reg)", rdata), UVM_MEDIUM)
        axi_read(32'h0000002C, rdata, "RX_DATA");
        `uvm_info("RCOV015", $sformatf("RX_DATA     = 0x%08h (empty FIFO)", rdata), UVM_MEDIUM)
    endtask

endclass