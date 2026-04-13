class buffered_axi_lite_uart_sequencer extends uvm_sequencer #(buffered_axi_lite_uart_seq_item);
    `uvm_component_utils(buffered_axi_lite_uart_sequencer)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
endclass