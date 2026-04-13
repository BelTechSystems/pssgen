// Regression test: runs smoke sequence followed by COV-001 baud tuning sweep.
// Additional COV sequences are added here as they are created.
// Start with: +UVM_TESTNAME=buffered_axi_lite_uart_regression_test
class buffered_axi_lite_uart_regression_test extends buffered_axi_lite_uart_base_test;
    `uvm_component_utils(buffered_axi_lite_uart_regression_test)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    virtual task run_sequences(uvm_phase phase);
        buffered_axi_lite_uart_smoke_seq  smoke;
        seq_RCOV001_baud_tuning           cov001;

        smoke  = buffered_axi_lite_uart_smoke_seq::type_id::create("smoke");
        cov001 = seq_RCOV001_baud_tuning::type_id::create("cov001");

        smoke.start(env_h.agent.seqr);
        cov001.start(env_h.agent.seqr);
    endtask

endclass
