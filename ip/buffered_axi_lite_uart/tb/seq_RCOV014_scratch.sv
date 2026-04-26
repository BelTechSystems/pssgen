// =============================================================================
// COV-014  SCRATCH
//
// Linked requirements:
//   UART-REG-044, UART-REG-045, UART-REG-046, UART-VER-003
//
// Stimulus strategy:
//   Write walking-ones (0x00000001 through 0x80000000), all-ones (0xFFFFFFFF), and all-zeros (0x00000000) to SCRATCH; read back and verify each value.
//
// Boundary values:
//   0x00000001..0x80000000 (walking ones), 0x000000FF, 0xFFFFFFFF (all-ones), 0x00000000 (all-zeros)
// =============================================================================

class seq_RCOV014_scratch extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV014_scratch)

    function new(string name = "seq_RCOV014_scratch");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Walking ones: each of the 8 power-of-two values up to 0x80000000
        bit [31:0] vals[10] = '{
            32'h00000001, 32'h00000002, 32'h00000004, 32'h00000008,
            32'h00000010, 32'h00000020, 32'h00000040, 32'h00000080,
            32'hFFFFFFFF,  // all-ones
            32'h00000000   // all-zeros
        };
        foreach (vals[i]) begin
            axi_write(32'h00000024, vals[i], 4'hF, "SCRATCH");
            axi_read (32'h00000024, rdata,   "SCRATCH");
            if (rdata !== vals[i])
                `uvm_error("RCOV014",
                    $sformatf("SCRATCH readback fail: wrote=0x%08h got=0x%08h", vals[i], rdata))
        end
    endtask

endclass