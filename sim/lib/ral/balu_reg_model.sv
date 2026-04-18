// ================================================================
// File       : balu_reg_model.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : UVM RAL register model for buffered_axi_lite_uart (BALU).
//              14 registers, 32-bit data width, AXI-Lite byte addressing.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Register map (base 0x0000):
//   0x00  CTRL      RW   bit0=TX_EN, bit1=RX_EN, bit4=LOOP_EN, bit7=SOFT_RESET
//   0x04  STATUS    RO   bit0=TX_EMPTY, bit1=RX_VALID, bit2=TX_FULL,
//                        bit3=RX_FULL, bit4=PARITY_ERR, bit5=FRAME_ERR,
//                        bit6=OVERRUN_ERR
//   0x08  BAUD      RW   [31:0] NCO tuning word
//   0x0C  TX_DATA   WO   [7:0] transmit data
//   0x10  RX_DATA   RO   [7:0] receive data
//   0x14  TX_FIFO   RO   [7:0] TX FIFO status
//   0x18  RX_FIFO   RO   [7:0] RX FIFO status
//   0x1C  IER       RW   [7:0] interrupt enable
//   0x20  ISR       W1C  [7:0] interrupt status (write-1-to-clear)
//   0x24  PARITY    RW   [1:0] parity config
//   0x28  FRAME     RW   [3:0] frame config
//   0x2C  SCRATCH   RW   [31:0] scratch
//   0x30  TIMEOUT   RW   [15:0] RX timeout
//   0x34  LOOPBACK  RW   bit0 loopback enable
//
// Dependencies:
//   uvm_pkg
//
// Portability    : Simulator-independent
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
// ================================================================

// ── CTRL (0x00) — RW ─────────────────────────────────────────────────────────
class balu_ctrl_reg extends uvm_reg;
    uvm_reg_field TX_EN;
    uvm_reg_field RX_EN;
    uvm_reg_field LOOP_EN;
    uvm_reg_field SOFT_RESET;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_ctrl_reg)
    function new(string name = "balu_ctrl_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TX_EN      = uvm_reg_field::type_id::create("TX_EN");
        RX_EN      = uvm_reg_field::type_id::create("RX_EN");
        LOOP_EN    = uvm_reg_field::type_id::create("LOOP_EN");
        SOFT_RESET = uvm_reg_field::type_id::create("SOFT_RESET");
        RESERVED   = uvm_reg_field::type_id::create("RESERVED");
        // configure(parent, size, lsb_pos, access, volatile, reset,
        //           has_reset, is_rand, individually_accessible)
        TX_EN.configure     (this,  1,  0, "RW", 0, 1'b0,  1, 1, 0);
        RX_EN.configure     (this,  1,  1, "RW", 0, 1'b0,  1, 1, 0);
        LOOP_EN.configure   (this,  1,  4, "RW", 0, 1'b0,  1, 1, 0);
        SOFT_RESET.configure(this,  1,  7, "RW", 0, 1'b0,  1, 1, 0);
        RESERVED.configure  (this, 24,  8, "RO", 0, 24'b0, 1, 0, 0);
    endfunction
endclass

// ── STATUS (0x04) — RO ────────────────────────────────────────────────────────
class balu_status_reg extends uvm_reg;
    uvm_reg_field TX_EMPTY;
    uvm_reg_field RX_VALID;
    uvm_reg_field TX_FULL;
    uvm_reg_field RX_FULL;
    uvm_reg_field PARITY_ERR;
    uvm_reg_field FRAME_ERR;
    uvm_reg_field OVERRUN_ERR;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_status_reg)
    function new(string name = "balu_status_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TX_EMPTY    = uvm_reg_field::type_id::create("TX_EMPTY");
        RX_VALID    = uvm_reg_field::type_id::create("RX_VALID");
        TX_FULL     = uvm_reg_field::type_id::create("TX_FULL");
        RX_FULL     = uvm_reg_field::type_id::create("RX_FULL");
        PARITY_ERR  = uvm_reg_field::type_id::create("PARITY_ERR");
        FRAME_ERR   = uvm_reg_field::type_id::create("FRAME_ERR");
        OVERRUN_ERR = uvm_reg_field::type_id::create("OVERRUN_ERR");
        RESERVED    = uvm_reg_field::type_id::create("RESERVED");
        TX_EMPTY.configure   (this, 1, 0, "RO", 1, 1'b1, 1, 0, 0);
        RX_VALID.configure   (this, 1, 1, "RO", 1, 1'b0, 1, 0, 0);
        TX_FULL.configure    (this, 1, 2, "RO", 1, 1'b0, 1, 0, 0);
        RX_FULL.configure    (this, 1, 3, "RO", 1, 1'b0, 1, 0, 0);
        PARITY_ERR.configure (this, 1, 4, "RO", 1, 1'b0, 1, 0, 0);
        FRAME_ERR.configure  (this, 1, 5, "RO", 1, 1'b0, 1, 0, 0);
        OVERRUN_ERR.configure(this, 1, 6, "RO", 1, 1'b0, 1, 0, 0);
        RESERVED.configure   (this, 25, 7, "RO", 0, 25'b0, 1, 0, 0);
    endfunction
endclass

// ── BAUD (0x08) — RW ─────────────────────────────────────────────────────────
class balu_baud_reg extends uvm_reg;
    uvm_reg_field NCO_WORD;

    `uvm_object_utils(balu_baud_reg)
    function new(string name = "balu_baud_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        NCO_WORD = uvm_reg_field::type_id::create("NCO_WORD");
        NCO_WORD.configure(this, 32, 0, "RW", 0, 32'h0, 1, 1, 0);
    endfunction
endclass

// ── TX_DATA (0x0C) — WO ───────────────────────────────────────────────────────
class balu_tx_data_reg extends uvm_reg;
    uvm_reg_field TX_BYTE;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_tx_data_reg)
    function new(string name = "balu_tx_data_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TX_BYTE  = uvm_reg_field::type_id::create("TX_BYTE");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        TX_BYTE.configure (this,  8, 0, "WO", 0, 8'h0,  1, 1, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── RX_DATA (0x10) — RO ───────────────────────────────────────────────────────
class balu_rx_data_reg extends uvm_reg;
    uvm_reg_field RX_BYTE;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_rx_data_reg)
    function new(string name = "balu_rx_data_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        RX_BYTE  = uvm_reg_field::type_id::create("RX_BYTE");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        RX_BYTE.configure (this,  8, 0, "RO", 1, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── TX_FIFO (0x14) — RO ───────────────────────────────────────────────────────
class balu_tx_fifo_reg extends uvm_reg;
    uvm_reg_field DEPTH;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_tx_fifo_reg)
    function new(string name = "balu_tx_fifo_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        DEPTH    = uvm_reg_field::type_id::create("DEPTH");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        DEPTH.configure   (this,  8, 0, "RO", 1, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── RX_FIFO (0x18) — RO ───────────────────────────────────────────────────────
class balu_rx_fifo_reg extends uvm_reg;
    uvm_reg_field DEPTH;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_rx_fifo_reg)
    function new(string name = "balu_rx_fifo_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        DEPTH    = uvm_reg_field::type_id::create("DEPTH");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        DEPTH.configure   (this,  8, 0, "RO", 1, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── IER (0x1C) — RW ──────────────────────────────────────────────────────────
class balu_ier_reg extends uvm_reg;
    uvm_reg_field IE_BITS;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_ier_reg)
    function new(string name = "balu_ier_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        IE_BITS  = uvm_reg_field::type_id::create("IE_BITS");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        IE_BITS.configure (this,  8, 0, "RW", 0, 8'h0,  1, 1, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── ISR (0x20) — W1C ─────────────────────────────────────────────────────────
class balu_isr_reg extends uvm_reg;
    uvm_reg_field IS_BITS;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_isr_reg)
    function new(string name = "balu_isr_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        IS_BITS  = uvm_reg_field::type_id::create("IS_BITS");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        IS_BITS.configure (this,  8, 0, "W1C", 1, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 24, 8, "RO",  0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── PARITY (0x24) — RW ────────────────────────────────────────────────────────
class balu_parity_reg extends uvm_reg;
    uvm_reg_field PAR_CFG;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_parity_reg)
    function new(string name = "balu_parity_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        PAR_CFG  = uvm_reg_field::type_id::create("PAR_CFG");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        PAR_CFG.configure (this,  2, 0, "RW", 0, 2'h0,  1, 1, 0);
        RESERVED.configure(this, 30, 2, "RO", 0, 30'h0, 1, 0, 0);
    endfunction
endclass

// ── FRAME (0x28) — RW ─────────────────────────────────────────────────────────
class balu_frame_reg extends uvm_reg;
    uvm_reg_field FRAME_CFG;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_frame_reg)
    function new(string name = "balu_frame_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        FRAME_CFG = uvm_reg_field::type_id::create("FRAME_CFG");
        RESERVED  = uvm_reg_field::type_id::create("RESERVED");
        FRAME_CFG.configure(this,  4, 0, "RW", 0, 4'h0,  1, 1, 0);
        RESERVED.configure (this, 28, 4, "RO", 0, 28'h0, 1, 0, 0);
    endfunction
endclass

// ── SCRATCH (0x2C) — RW ───────────────────────────────────────────────────────
class balu_scratch_reg extends uvm_reg;
    uvm_reg_field SCRATCH_DATA;

    `uvm_object_utils(balu_scratch_reg)
    function new(string name = "balu_scratch_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        SCRATCH_DATA = uvm_reg_field::type_id::create("SCRATCH_DATA");
        SCRATCH_DATA.configure(this, 32, 0, "RW", 0, 32'h0, 1, 1, 0);
    endfunction
endclass

// ── TIMEOUT (0x30) — RW ───────────────────────────────────────────────────────
class balu_timeout_reg extends uvm_reg;
    uvm_reg_field TO_VAL;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_timeout_reg)
    function new(string name = "balu_timeout_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TO_VAL   = uvm_reg_field::type_id::create("TO_VAL");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        TO_VAL.configure  (this, 16,  0, "RW", 0, 16'h0, 1, 1, 0);
        RESERVED.configure(this, 16, 16, "RO", 0, 16'h0, 1, 0, 0);
    endfunction
endclass

// ── LOOPBACK (0x34) — RW ──────────────────────────────────────────────────────
class balu_loopback_reg extends uvm_reg;
    uvm_reg_field LB_EN;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_loopback_reg)
    function new(string name = "balu_loopback_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        LB_EN    = uvm_reg_field::type_id::create("LB_EN");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        LB_EN.configure   (this,  1,  0, "RW", 0, 1'b0,  1, 1, 0);
        RESERVED.configure(this, 31,  1, "RO", 0, 31'b0, 1, 0, 0);
    endfunction
endclass

// ── Top-level register block ──────────────────────────────────────────────────
class balu_reg_model extends uvm_reg_block;

    `uvm_object_utils(balu_reg_model)

    // One handle per register
    rand balu_ctrl_reg     CTRL;
    rand balu_status_reg   STATUS;
    rand balu_baud_reg     BAUD;
    rand balu_tx_data_reg  TX_DATA;
    rand balu_rx_data_reg  RX_DATA;
    rand balu_tx_fifo_reg  TX_FIFO;
    rand balu_rx_fifo_reg  RX_FIFO;
    rand balu_ier_reg      IER;
    rand balu_isr_reg      ISR;
    rand balu_parity_reg   PARITY;
    rand balu_frame_reg    FRAME;
    rand balu_scratch_reg  SCRATCH;
    rand balu_timeout_reg  TIMEOUT;
    rand balu_loopback_reg LOOPBACK;

    uvm_reg_map default_map;

    function new(string name = "balu_reg_model");
        super.new(name, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        // Create and configure each register
        CTRL    = balu_ctrl_reg::type_id::create("CTRL");
        CTRL.build(); CTRL.configure(this, null, "");

        STATUS  = balu_status_reg::type_id::create("STATUS");
        STATUS.build(); STATUS.configure(this, null, "");

        BAUD    = balu_baud_reg::type_id::create("BAUD");
        BAUD.build(); BAUD.configure(this, null, "");

        TX_DATA = balu_tx_data_reg::type_id::create("TX_DATA");
        TX_DATA.build(); TX_DATA.configure(this, null, "");

        RX_DATA = balu_rx_data_reg::type_id::create("RX_DATA");
        RX_DATA.build(); RX_DATA.configure(this, null, "");

        TX_FIFO = balu_tx_fifo_reg::type_id::create("TX_FIFO");
        TX_FIFO.build(); TX_FIFO.configure(this, null, "");

        RX_FIFO = balu_rx_fifo_reg::type_id::create("RX_FIFO");
        RX_FIFO.build(); RX_FIFO.configure(this, null, "");

        IER     = balu_ier_reg::type_id::create("IER");
        IER.build(); IER.configure(this, null, "");

        ISR     = balu_isr_reg::type_id::create("ISR");
        ISR.build(); ISR.configure(this, null, "");

        PARITY  = balu_parity_reg::type_id::create("PARITY");
        PARITY.build(); PARITY.configure(this, null, "");

        FRAME   = balu_frame_reg::type_id::create("FRAME");
        FRAME.build(); FRAME.configure(this, null, "");

        SCRATCH = balu_scratch_reg::type_id::create("SCRATCH");
        SCRATCH.build(); SCRATCH.configure(this, null, "");

        TIMEOUT = balu_timeout_reg::type_id::create("TIMEOUT");
        TIMEOUT.build(); TIMEOUT.configure(this, null, "");

        LOOPBACK = balu_loopback_reg::type_id::create("LOOPBACK");
        LOOPBACK.build(); LOOPBACK.configure(this, null, "");

        // Build address map: base=0, bus_width=4 bytes, little-endian
        default_map = create_map("default_map", 0, 4, UVM_LITTLE_ENDIAN);
        default_map.add_reg(CTRL,     32'h00, "RW");
        default_map.add_reg(STATUS,   32'h04, "RO");
        default_map.add_reg(BAUD,     32'h08, "RW");
        default_map.add_reg(TX_DATA,  32'h0C, "WO");
        default_map.add_reg(RX_DATA,  32'h10, "RO");
        default_map.add_reg(TX_FIFO,  32'h14, "RO");
        default_map.add_reg(RX_FIFO,  32'h18, "RO");
        default_map.add_reg(IER,      32'h1C, "RW");
        default_map.add_reg(ISR,      32'h20, "RW");
        default_map.add_reg(PARITY,   32'h24, "RW");
        default_map.add_reg(FRAME,    32'h28, "RW");
        default_map.add_reg(SCRATCH,  32'h2C, "RW");
        default_map.add_reg(TIMEOUT,  32'h30, "RW");
        default_map.add_reg(LOOPBACK, 32'h34, "RW");

        lock_model();
    endfunction

endclass
