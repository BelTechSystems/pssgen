`ifndef BUFFERED_AXI_LITE_UART_SEQ_ITEM_SV
`define BUFFERED_AXI_LITE_UART_SEQ_ITEM_SV

//------------------------------------------------------------------------------
// File: buffered_axi_lite_uart_seq_item.sv
// Description:
//   UVM sequence item for the Buffered AXI-Lite UART testbench.
//   Represents one AXI-Lite register access transaction.
//
// Notes:
//   - Supports single-beat AXI-Lite reads and writes.
//   - Keeps stimulus fields separate from response fields.
//   - Includes simple randomization constraints for aligned register access.
//------------------------------------------------------------------------------

class buffered_axi_lite_uart_seq_item extends uvm_sequence_item;

    //--------------------------------------------------------------------------
    // Type used to describe the requested bus operation
    //--------------------------------------------------------------------------
    typedef enum logic [0:0] {
        AXI_READ  = 1'b0,
        AXI_WRITE = 1'b1
    } axi_cmd_e;

    //--------------------------------------------------------------------------
    // Stimulus fields
    //--------------------------------------------------------------------------
    rand axi_cmd_e    cmd;
    rand bit [31:0]   addr;
    rand bit [31:0]   wdata;
    rand bit [3:0]    wstrb;

    // Optional timing knob for bus stress testing
    rand int unsigned pre_delay_cycles;

    //--------------------------------------------------------------------------
    // Response / observation fields
    //--------------------------------------------------------------------------
    bit [31:0]        rdata;
    bit [1:0]         resp;

    // Optional bookkeeping / checking aids
    string            reg_name;
    bit               expect_error;
    bit [31:0]        expected_rdata;

    //--------------------------------------------------------------------------
    // Constraints
    //--------------------------------------------------------------------------
    // AXI-Lite registers are 32-bit aligned
    constraint c_addr_aligned {
        addr[1:0] == 2'b00;
    }

    // Keep delay small by default for fast regression runtime
    constraint c_pre_delay_cycles {
        pre_delay_cycles inside {[0:10]};
    }

    // Default strobes:
    // - Writes default to full word access
    // - Reads keep strobes at zero
    constraint c_wstrb_by_cmd {
        if (cmd == AXI_WRITE) {
            wstrb != 4'b0000;
        } else {
            wstrb == 4'b0000;
        }
    }

    //--------------------------------------------------------------------------
    // UVM automation
    //--------------------------------------------------------------------------
    `uvm_object_utils_begin(buffered_axi_lite_uart_seq_item)
        `uvm_field_enum(axi_cmd_e,  cmd,             UVM_DEFAULT)
        `uvm_field_int(addr,                         UVM_HEX)
        `uvm_field_int(wdata,                        UVM_HEX)
        `uvm_field_int(wstrb,                        UVM_BIN)
        `uvm_field_int(pre_delay_cycles,             UVM_DEC)
        `uvm_field_int(rdata,                        UVM_HEX | UVM_NOCOMPARE)
        `uvm_field_int(resp,                         UVM_BIN | UVM_NOCOMPARE)
        `uvm_field_string(reg_name,                  UVM_DEFAULT)
        `uvm_field_int(expect_error,                 UVM_DEFAULT)
        `uvm_field_int(expected_rdata,               UVM_HEX)
    `uvm_object_utils_end

    //--------------------------------------------------------------------------
    // Constructor
    //--------------------------------------------------------------------------
    function new(string name = "buffered_axi_lite_uart_seq_item");
        super.new(name);
        reg_name        = "";
        expect_error    = 1'b0;
        expected_rdata  = '0;
        rdata           = '0;
        resp            = 2'b00;
    endfunction

    //--------------------------------------------------------------------------
    // Convenience helpers
    //--------------------------------------------------------------------------
    function bit is_read();
        return (cmd == AXI_READ);
    endfunction

    function bit is_write();
        return (cmd == AXI_WRITE);
    endfunction

    //--------------------------------------------------------------------------
    // Convert to readable string for logs / debug
    //--------------------------------------------------------------------------
    function string convert2string();
        string cmd_str;
        cmd_str = (cmd == AXI_WRITE) ? "WRITE" : "READ";

        return $sformatf(
            "cmd=%s addr=0x%08h wdata=0x%08h wstrb=0x%1h pre_delay=%0d rdata=0x%08h resp=0x%0h reg_name=%s expect_error=%0b expected_rdata=0x%08h",
            cmd_str,
            addr,
            wdata,
            wstrb,
            pre_delay_cycles,
            rdata,
            resp,
            reg_name,
            expect_error,
            expected_rdata
        );
    endfunction

    //--------------------------------------------------------------------------
    // Optional helper to set up a write quickly
    //--------------------------------------------------------------------------
    function void set_write(
        bit [31:0] addr_in,
        bit [31:0] data_in,
        bit [3:0]  strb_in = 4'hF,
        string     reg_name_in = ""
    );
        cmd      = AXI_WRITE;
        addr     = addr_in;
        wdata    = data_in;
        wstrb    = strb_in;
        reg_name = reg_name_in;
    endfunction

    //--------------------------------------------------------------------------
    // Optional helper to set up a read quickly
    //--------------------------------------------------------------------------
    function void set_read(
        bit [31:0] addr_in,
        string     reg_name_in = ""
    );
        cmd      = AXI_READ;
        addr     = addr_in;
        wdata    = '0;
        wstrb    = '0;
        reg_name = reg_name_in;
    endfunction

endclass

`endif