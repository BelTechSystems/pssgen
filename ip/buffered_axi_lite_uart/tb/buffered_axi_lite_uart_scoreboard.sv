class buffered_axi_lite_uart_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(buffered_axi_lite_uart_scoreboard)

    uvm_analysis_imp #(buffered_axi_lite_uart_seq_item,
                       buffered_axi_lite_uart_scoreboard) analysis_export;

    // Shadow register model — RW registers only.
    // RO and WO registers are not predicted here.
    local bit [31:0] shadow [bit [31:0]];

    // Running error count reported in check_phase.
    local int error_count;

    function new(string name, uvm_component parent);
        super.new(name, parent);
        error_count = 0;
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        analysis_export = new("analysis_export", this);
        _init_shadow();
    endfunction

    // Pre-load RW register reset values.
    // STATUS reset = 0x00000140 (TX_EMPTY[8]=1, RX_EMPTY[6]=1 — confirmed
    // against VHDL STATUS_p process; regmap context value 0x300 is incorrect).
    // RO and side-effect registers (STATUS, FIFO_STATUS, INT_STATUS,
    // INT_CLEAR, TX_DATA, RX_DATA) are omitted from the shadow.
    local function void _init_shadow();
        shadow[32'h00] = 32'h00000000;   // CTRL
        shadow[32'h08] = 32'h004FA6D5;   // BAUD_TUNING
        shadow[32'h0C] = 32'h00000808;   // FIFO_CTRL (16-bit register, reset=G_FIFO_DEPTH/2 & G_FIFO_DEPTH/2)
        shadow[32'h14] = 32'h00000064;   // TIMEOUT_VAL (16-bit register, reset=0x0064)
        shadow[32'h18] = 32'h00000000;   // INT_ENABLE
        shadow[32'h24] = 32'h00000000;   // SCRATCH
    endfunction

    // Apply a write to the shadow, honouring wstrb byte-enable masking.
    local function void _apply_write(
        bit [31:0] addr,
        bit [31:0] wdata,
        bit [3:0]  wstrb
    );
        for (int b = 0; b < 4; b++) begin
            if (wstrb[b])
                shadow[addr][b*8 +: 8] = wdata[b*8 +: 8];
        end
        // TIMEOUT_VAL and FIFO_CTRL are 16-bit — RTL ignores upper bits
        if (addr[7:0] === 8'h14 || addr[7:0] === 8'h0C)
            shadow[addr] = shadow[addr] & 32'h0000FFFF;
    endfunction

    function void write(buffered_axi_lite_uart_seq_item item);
        bit [7:0] reg_offset = item.addr[7:0];

        if (item.cmd === buffered_axi_lite_uart_seq_item::AXI_WRITE) begin

            case (reg_offset)
                8'h00, 8'h0C, 8'h14, 8'h18, 8'h24: begin
                    // RW register — update shadow with wstrb masking
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-006: write response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end else begin
                        _apply_write(item.addr, item.wdata, item.wstrb);
                    end
                end
                8'h08: begin
                    // BAUD_TUNING — write ignored while UART_EN (CTRL[7]) is set
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-006: write response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end else if (shadow[32'h00][7] === 1'b1) begin
                        `uvm_info("SB", $sformatf(
                            "BAUD_TUNING write ignored — UART_EN=1, per UART-BR-004 (wdata=0x%08h)",
                            item.wdata), UVM_MEDIUM)
                    end else begin
                        _apply_write(item.addr, item.wdata, item.wstrb);
                    end
                end
                8'h20: begin
                    // INT_CLEAR: W1C side-effect register — shadow not updated
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-006: write response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end
                end
                8'h28: begin
                    // TX_DATA: WO — no shadow entry
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-006: write response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end
                end
                8'h04, 8'h10, 8'h1C, 8'h2C: begin
                    // RO register — SLVERR is correct and expected per UART-IF-010/011
                    if (item.resp === 2'b10) begin
                        `uvm_info("SB", $sformatf(
                            "Write to RO register returned SLVERR (expected) — addr=0x%08h",
                            item.addr), UVM_MEDIUM)
                    end else begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-010: write to RO register did not return SLVERR — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end
                end
                default: begin
                    if (item.resp !== 2'b00) begin
                        `uvm_info("SB", $sformatf(
                            "Write to unknown register returned non-OKAY resp=%02b (expected for undefined space) — addr=0x%08h",
                            item.resp, item.addr), UVM_MEDIUM)
                    end else begin
                        `uvm_warning("SB", $sformatf(
                            "Write to unknown register returned OKAY — addr=0x%08h wdata=0x%08h",
                            item.addr, item.wdata))
                    end
                end
            endcase

        end else begin  // AXI_READ

            case (reg_offset)
                8'h00, 8'h0C, 8'h14, 8'h18, 8'h24: begin
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-007: read response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end else if (item.rdata !== shadow[item.addr]) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-REG: register readback mismatch — addr=0x%08h expected=0x%08h actual=0x%08h",
                            item.addr, shadow[item.addr], item.rdata))
                    end
                end
                8'h08: begin
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-007: read response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end else if (item.rdata !== shadow[item.addr]) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-REG-027: BAUD_TUNING readback mismatch — expected=0x%08h actual=0x%08h",
                            shadow[item.addr], item.rdata))
                    end
                end
                8'h20: begin
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-007: read response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end else if (item.rdata !== 32'h00000000) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "INT_CLEAR reads non-zero — expected=0x00000000 actual=0x%08h",
                            item.rdata))
                    end
                end
                8'h04, 8'h10, 8'h1C, 8'h2C: begin
                    if (item.resp !== 2'b00) begin
                        error_count++;
                        `uvm_error("SB", $sformatf(
                            "UART-IF-007: read response not OKAY — addr=0x%08h resp=%02b",
                            item.addr, item.resp))
                    end else begin
                        `uvm_info("SB", $sformatf(
                            "RO register read — addr=0x%08h rdata=0x%08h",
                            item.addr, item.rdata), UVM_HIGH)
                    end
                end
                8'h28: begin
                    // TX_DATA: WO register — read returns 0x00000000, no check
                    `uvm_info("SB", $sformatf(
                        "TX_DATA (WO) read — addr=0x%08h rdata=0x%08h",
                        item.addr, item.rdata), UVM_HIGH)
                end
                default: begin
                    // SLVERR on undefined address space is correct per spec
                    if (item.resp === 2'b10) begin
                        `uvm_info("SB", $sformatf(
                            "Read from unknown register returned SLVERR (expected) — addr=0x%08h",
                            item.addr), UVM_MEDIUM)
                    end else begin
                        `uvm_warning("SB", $sformatf(
                            "Read from unknown register addr=0x%08h rdata=0x%08h resp=%02b",
                            item.addr, item.rdata, item.resp))
                    end
                end
            endcase
        end
    endfunction

    function void check_phase(uvm_phase phase);
        `uvm_info("SB", $sformatf(
            "Scoreboard check_phase: %0d error(s)", error_count), UVM_MEDIUM)
    endfunction

endclass
