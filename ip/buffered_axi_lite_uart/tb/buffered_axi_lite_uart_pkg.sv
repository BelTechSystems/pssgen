package buffered_axi_lite_uart_pkg;
    // Bring in UVM for the whole package
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    // Include the class files in strict dependency order
    `include "buffered_axi_lite_uart_seq_item.sv"   // no dependencies
    `include "buffered_axi_lite_uart_seqr.sv"       // depends on seq_item
    `include "buffered_axi_lite_uart_driver.sv"     // depends on seq_item
    `include "buffered_axi_lite_uart_monitor.sv"    // depends on seq_item
    `include "buffered_axi_lite_uart_base_seq.sv"   // depends on seq_item
    `include "buffered_axi_lite_uart_smoke_seq.sv"  // depends on base_seq
    `include "seq_RCOV001_baud_tuning.sv"           // depends on base_seq
    `include "buffered_axi_lite_uart_agent.sv"      // depends on drv/mon/seqr
    `include "buffered_axi_lite_uart_test.sv"       // depends on agent, seqs
endpackage
