class buffered_axi_lite_uart_driver extends uvm_driver #(uvm_sequence_item);
    `uvm_component_utils(buffered_axi_lite_uart_driver)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
    endfunction

    task run_phase(uvm_phase phase);
        // Drives transactions from the sequencer onto the virtual interface.
        // Extend: add virtual buffered_axi_lite_uart_if vif and
        // seq_item_port.get_next_item() / item_done() loop.
        phase.raise_objection(this);
        phase.drop_objection(this);
    endtask
endclass