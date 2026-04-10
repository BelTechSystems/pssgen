class buffered_axi_lite_uart_agent extends uvm_agent;
    `uvm_component_utils(buffered_axi_lite_uart_agent)

    buffered_axi_lite_uart_driver drv;
    buffered_axi_lite_uart_monitor mon;
    buffered_axi_lite_uart_sequencer seqr;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        drv = buffered_axi_lite_uart_driver::type_id::create("drv", this);
        mon = buffered_axi_lite_uart_monitor::type_id::create("mon", this);
        seqr = buffered_axi_lite_uart_sequencer::type_id::create("seqr", this);
    endfunction
endclass