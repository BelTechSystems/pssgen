// =============================================================================
// COV-001  BAUD_TUNING — NCO tuning word register sweep
//
// Linked requirements:
//   UART-BR-001, UART-BR-002, UART-BR-003, UART-BR-005, UART-BR-006,
//   UART-PAR-004, UART-PAR-005, UART-PAR-007, UART-REG-026, UART-REG-027
//
// Stimulus strategy (verbatim from VPR):
//   NCO tuning word sweep at 12 values from minimum (0x00000001) to
//   maximum (0xFFFFFFFF) including all standard baud rates.
//
// Tuning word formula: round(baud_rate * 2^32 / G_CLK_FREQ_HZ)
// G_CLK_FREQ_HZ = 100_000_000 (100 MHz)
//
// BAUD_TUNING register: offset 0x08 per register map.
// Write to BAUD_TUNING requires UART_EN=0 (reset default). Req: UART-BR-004.
//
// Readback checking has moved to buffered_axi_lite_uart_scoreboard.
// The axi_read call is retained so the monitor observes the transaction.
// =============================================================================

class seq_RCOV001_baud_tuning extends buffered_axi_lite_uart_base_seq;

    `uvm_object_utils(seq_RCOV001_baud_tuning)

    function new(string name = "seq_RCOV001_baud_tuning");
        super.new(name);
    endfunction

    virtual task body();
        // 12-value NCO tuning word sweep.
        // Values: round(baud * 2^32 / 100_000_000) for each baud rate.
        bit [31:0] tuning_words [12] = '{
            32'h00000001,   //        1 — minimum boundary
            32'h00064A9D,   //     9600 baud
            32'h000C953A,   //    19200 baud
            32'h00192A73,   //    38400 baud
            32'h0025BFAD,   //    57600 baud
            32'h004B7F5A,   //   115200 baud
            32'h0096FEB5,   //   230400 baud
            32'h012DFD69,   //   460800 baud
            32'h025BFAD3,   //   921600 baud
            32'h01EB851F,   //   750000 baud
            32'h07AE147B,   //  3000000 baud (3/4 Mbaud)
            32'hFFFFFFFF    // maximum boundary
        };

        string baud_names [12] = '{
            "min_boundary",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
            "230400",
            "460800",
            "921600",
            "750000",
            "3000000",
            "max_boundary"
        };

        bit [31:0] rdata;

        for (int i = 0; i < 12; i++) begin
            // Write tuning word
            axi_write(32'h00000008, tuning_words[i], 4'hF, "BAUD_TUNING");

            // Read back — scoreboard performs the comparison check
            axi_read(32'h00000008, rdata, "BAUD_TUNING");

            `uvm_info("RCOV001",
                $sformatf("BAUD_TUNING [%s] write=0x%08h readback=0x%08h",
                    baud_names[i], tuning_words[i], rdata),
                UVM_MEDIUM)
        end
    endtask

endclass
