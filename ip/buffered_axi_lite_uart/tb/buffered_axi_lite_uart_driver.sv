class buffered_axi_lite_uart_driver extends uvm_driver #(buffered_axi_lite_uart_seq_item);
    `uvm_component_utils(buffered_axi_lite_uart_driver)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
    endfunction

    task run_phase(uvm_phase phase);
        buffered_axi_lite_uart_seq_item req;
        forever begin
            seq_item_port.get_next_item(req);
            // Extend: drive req fields onto vif — add vif handle in build_phase
            seq_item_port.item_done();
        end
    endtask
endclass