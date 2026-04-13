class buffered_axi_lite_uart_base_seq extends
    uvm_sequence #(buffered_axi_lite_uart_seq_item);

    `uvm_object_utils(buffered_axi_lite_uart_base_seq)

    function new(string name = "buffered_axi_lite_uart_base_seq");
        super.new(name);
    endfunction

    // Convenience task: perform one AXI-Lite write and wait for BVALID.
    // The driver handles handshaking; this task just creates and sends
    // the item.
    virtual task axi_write(input bit [31:0] addr,
                           input bit [31:0] data,
                           input bit [3:0]  strb     = 4'hF,
                           input string     reg_name = "");
        buffered_axi_lite_uart_seq_item item;
        item = buffered_axi_lite_uart_seq_item::type_id::create("item");
        start_item(item);
        item.set_write(addr, data, strb, reg_name);
        finish_item(item);
    endtask

    // Convenience task: perform one AXI-Lite read.
    virtual task axi_read(input  bit [31:0] addr,
                          output bit [31:0] rdata,
                          input  string     reg_name = "");
        buffered_axi_lite_uart_seq_item item;
        item = buffered_axi_lite_uart_seq_item::type_id::create("item");
        start_item(item);
        item.set_read(addr, reg_name);
        finish_item(item);
        rdata = item.rdata;
    endtask

endclass
