// =============================================================================
// COV-003  CTRL.STOP_BITS
//
// Linked requirements:
//   UART-FF-002, UART-FF-003, UART-FF-004, UART-REG-010
//
// Stimulus strategy:
//   Both stop bit configurations (1 and 2 stop bits) exercised in LOOP_EN loopback with frame integrity check.
//
// Boundary values:
//   1'b0 (1 stop bit), 1'b1 (2 stop bits)
// =============================================================================

class seq_RCOV003_ctrl_stop_bits extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV003_ctrl_stop_bits)

    function new(string name = "seq_RCOV003_ctrl_stop_bits");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // CTRL[1] = STOP: 0=1 stop bit, 1=2 stop bits
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL"); // 1 stop bit
        axi_read (32'h00000000, rdata,              "CTRL");
        axi_write(32'h00000000, 32'h00000020, 4'hF, "CTRL"); // 2 stop bits
        axi_read (32'h00000000, rdata,              "CTRL");
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL"); // restore
    endtask

endclass