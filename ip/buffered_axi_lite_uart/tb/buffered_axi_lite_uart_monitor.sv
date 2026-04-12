class buffered_axi_lite_uart_monitor extends uvm_monitor;
    `uvm_component_utils(buffered_axi_lite_uart_monitor)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void write(uvm_sequence_item item);
        // Publishes observed transactions to the analysis port.
        // Extend: add analysis_port.write(item) after sampling the virtual interface.
    endfunction
endclass