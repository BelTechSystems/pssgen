// =============================================================================
// COV-006  TIMEOUT_VAL
//
// Linked requirements:
//   UART-TO-001, UART-TO-002, UART-TO-003, UART-TO-004, UART-TO-005, UART-TO-006, UART-REG-035, UART-REG-036, UART-PAR-006, UART-VER-008
//
// Stimulus strategy:
//   TIMEOUT_VAL set to 0x0000, 0x0001, G_TIMEOUT_DEFAULT, 0xFFFE, and 0xFFFF; idle receiver until timeout fires for each non-zero value.
//
// Boundary values:
//   0x0000 (disabled), 0x0001 (minimum active), G_TIMEOUT_DEFAULT (reset), 0xFFFE, 0xFFFF (maximum)
// =============================================================================

class seq_RCOV006_timeout_val extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV006_timeout_val)

    function new(string name = "seq_RCOV006_timeout_val");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Five boundary values per VPR COV-006 (16-bit field, upper bits ignored)
        bit [31:0] vals[5] = '{32'h00000000, 32'h00000001, 32'h00049A58, 32'h0000FFFE, 32'h0000FFFF};
        // 0x00049A58 = 301656 — representative of a 3 ms timeout at 100 MHz
        foreach (vals[i]) begin
            axi_write(32'h00000014, vals[i], 4'hF, "TIMEOUT_VAL");
            axi_read (32'h00000014, rdata,   "TIMEOUT_VAL");
            `uvm_info("RCOV006",
                $sformatf("TIMEOUT_VAL wrote 0x%08h readback 0x%08h", vals[i], rdata),
                UVM_MEDIUM)
        end
    endtask

endclass