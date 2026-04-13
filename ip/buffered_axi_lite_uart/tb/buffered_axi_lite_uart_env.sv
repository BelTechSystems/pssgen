class buffered_axi_lite_uart_env extends uvm_env;
    `uvm_component_utils(buffered_axi_lite_uart_env)

    buffered_axi_lite_uart_agent                   agent;
    buffered_axi_lite_uart_scoreboard              sb;
    buffered_axi_lite_uart_coverage_subscriber     cov;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        agent = buffered_axi_lite_uart_agent::type_id::create("agent", this);
        sb    = buffered_axi_lite_uart_scoreboard::type_id::create("sb", this);
        cov   = buffered_axi_lite_uart_coverage_subscriber::type_id::create("cov", this);
    endfunction

    function void connect_phase(uvm_phase phase);
        agent.mon.ap.connect(sb.analysis_export);
        agent.mon.ap.connect(cov.analysis_export);
    endfunction

endclass
