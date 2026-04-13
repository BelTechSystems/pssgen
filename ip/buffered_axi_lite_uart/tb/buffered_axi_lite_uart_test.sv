// Base test: owns the env and provides the raise/drop objection wrapper.
// Subclasses override run_sequences() to supply stimulus.
class buffered_axi_lite_uart_base_test extends uvm_test;
    `uvm_component_utils(buffered_axi_lite_uart_base_test)

    buffered_axi_lite_uart_env env_h;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        env_h = buffered_axi_lite_uart_env::type_id::create("env_h", this);
    endfunction

    task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        run_sequences(phase);
        phase.drop_objection(this);
    endtask

    // Override in subclass to run sequences. Base does nothing.
    virtual task run_sequences(uvm_phase phase);
    endtask

endclass


// Smoke test: runs buffered_axi_lite_uart_smoke_seq end-to-end.
// Start with: +UVM_TESTNAME=buffered_axi_lite_uart_smoke_test
class buffered_axi_lite_uart_smoke_test extends buffered_axi_lite_uart_base_test;
    `uvm_component_utils(buffered_axi_lite_uart_smoke_test)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    virtual task run_sequences(uvm_phase phase);
        buffered_axi_lite_uart_smoke_seq seq;
        seq = buffered_axi_lite_uart_smoke_seq::type_id::create("seq");
        seq.start(env_h.agent.seqr);
    endtask

endclass
