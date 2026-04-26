// =============================================================================
// COV-013  BAUD_TUNING_WRITE_WHILE_ENABLED
//
// Linked requirements:
//   UART-REG-028, UART-VER-007
//
// Stimulus strategy:
//   Assert UART_EN, write a new value to BAUD_TUNING, read back and verify original value unchanged; confirms silent-ignore while enabled.
//
// Boundary values:
//   UART_EN=1, write new value, readback must equal original value
// =============================================================================

class seq_RCOV013_baud_tuning_write_while_enabled extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV013_baud_tuning_write_while_enabled)

    function new(string name = "seq_RCOV013_baud_tuning_write_while_enabled");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata_before, rdata_after;
        // Read original BAUD_TUNING value (set by RCOV001 — may not be reset value)
        axi_read(32'h00000008, rdata_before, "BAUD_TUNING");
        // Assert UART_EN (bit 7); BAUD_TUNING write is silently ignored when UART_EN=1
        axi_write(32'h00000000, 32'h00000080, 4'hF, "CTRL");
        // Attempt write — DUT shall ignore this (UART-REG-028)
        axi_write(32'h00000008, 32'hDEADBEEF, 4'hF, "BAUD_TUNING");
        // Readback must equal rdata_before
        axi_read(32'h00000008, rdata_after, "BAUD_TUNING");
        if (rdata_before !== rdata_after)
            `uvm_error("RCOV013",
                $sformatf("BAUD_TUNING changed while UART_EN=1: before=0x%08h after=0x%08h",
                    rdata_before, rdata_after))
        // Disable UART to restore state for subsequent sequences
        axi_write(32'h00000000, 32'h00000000, 4'hF, "CTRL");
    endtask

endclass