// BAUD_TUNING register: offset 0x08 per register map (regmap.xlsx RegisterMap sheet).
// Task spec listed 0x14, which is TIMEOUT_VAL — corrected to 0x08.

class buffered_axi_lite_uart_smoke_seq extends
    buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(buffered_axi_lite_uart_smoke_seq)

    function new(string name = "buffered_axi_lite_uart_smoke_seq");
        super.new(name);
    endfunction

    virtual task body();
        bit [31:0] rdata;
        // Write a known value to BAUD_TUNING (reset value: 0x004FA6D5)
        axi_write(32'h00000008, 32'h004FA6D5, 4'hF, "BAUD_TUNING");
        // Read it back
        axi_read(32'h00000008, rdata, "BAUD_TUNING");
        `uvm_info("SMOKE_SEQ",
            $sformatf("BAUD_TUNING readback = 0x%08h", rdata),
            UVM_MEDIUM)
    endtask

endclass
