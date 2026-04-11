class buffered_axi_lite_uart_monitor extends uvm_monitor;
    `uvm_component_utils(buffered_axi_lite_uart_monitor)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void write(uvm_sequence_item item);
        // Publish observed AXI-Lite transactions to the analysis port.
        // Scaffold: extend with analysis_port.write(item) after sampling vif.
    endfunction
endclass
