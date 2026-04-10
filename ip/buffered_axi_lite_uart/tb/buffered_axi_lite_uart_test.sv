class buffered_axi_lite_uart_test extends uvm_test;
    `uvm_component_utils(buffered_axi_lite_uart_test)

    buffered_axi_lite_uart_agent agent_h;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        agent_h = buffered_axi_lite_uart_agent::type_id::create("agent_h", this);
    endfunction
endclass