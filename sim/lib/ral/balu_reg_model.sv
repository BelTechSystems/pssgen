// ================================================================
// File       : balu_reg_model.sv
// Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
// Copyright  : Copyright (c) 2026 BelTech Systems LLC
// License    : MIT License — see LICENSE for details
// ================================================================
// Brief      : UVM RAL register model for buffered_axi_lite_uart (BALU).
//              12 registers, 32-bit data width, AXI-Lite byte addressing.
//              Derived from buffered_axi_lite_uart.vhd RTL constants.
// Document   : BelTech-STD-003 Rev 1
// Standard   : SystemVerilog IEEE 1800-2017 / UVM 1.2
//
// Register map (base 0x0000):
//   0x00  CTRL        RW   [7]=UART_EN [6]=TX_EN [5]=RX_EN [4]=LOOP_EN
//                          [3:2]=PARITY[1:0] [1]=STOP_BITS
//   0x04  STATUS      RO   [11]=TIMEOUT_FLAG [10]=IRQ_PENDING
//                          [9]=TX_FULL [8]=TX_EMPTY [7]=RX_FULL [6]=RX_EMPTY
//                          [5]=TX_BUSY [4]=RX_BUSY [3]=PARITY_ERR
//                          [2]=FRAME_ERR [1]=OVERRUN
//   0x08  BAUD_TUNING RW   [31:0] NCO tuning word
//   0x0C  FIFO_CTRL   RW   [15:8]=TX_THRESH [7:0]=RX_THRESH
//   0x10  FIFO_STATUS RO   [15:8]=TX_LEVEL  [7:0]=RX_LEVEL
//   0x14  TIMEOUT_VAL RW   [15:0] RX timeout in baud ticks
//   0x18  INT_ENABLE  RW   [7]=IE_TIMEOUT [6]=IE_TX_THRESH [5]=IE_RX_THRESH
//                          [4]=IE_TX_EMPTY [3]=IE_RX_FULL [2]=IE_PARITY_ERR
//                          [1]=IE_FRAME_ERR [0]=IE_OVERRUN
//   0x1C  INT_STATUS  RO   same bit mapping as INT_ENABLE (sticky W1C via INT_CLEAR)
//   0x20  INT_CLEAR   WO   write 1 to clear corresponding INT_STATUS bits
//   0x24  SCRATCH     RW   [31:0] read/write scratch, no hardware function
//   0x28  TX_DATA     WO   [7:0] transmit byte; reads return 0
//   0x2C  RX_DATA     RO   [7:0] receive byte (pops RX FIFO)
//
// Dependencies:
//   uvm_pkg
//
// Portability    : Simulator-independent
// Impl. status   : complete
//
// History:
//   2026-04-18  pssgen  sim/lib reusable AXI-Lite BFM library — Session 1
//   2026-04-19  pssgen  RAL Session 3: corrected to match actual BALU RTL
// ================================================================

// ── CTRL (0x00) — RW ─────────────────────────────────────────────────────────
class balu_ctrl_reg extends uvm_reg;
    uvm_reg_field UART_EN;
    uvm_reg_field TX_EN;
    uvm_reg_field RX_EN;
    uvm_reg_field LOOP_EN;
    uvm_reg_field PARITY;
    uvm_reg_field STOP_BITS;
    uvm_reg_field RSVD0;
    uvm_reg_field RSVD1;

    `uvm_object_utils(balu_ctrl_reg)
    function new(string name = "balu_ctrl_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        UART_EN   = uvm_reg_field::type_id::create("UART_EN");
        TX_EN     = uvm_reg_field::type_id::create("TX_EN");
        RX_EN     = uvm_reg_field::type_id::create("RX_EN");
        LOOP_EN   = uvm_reg_field::type_id::create("LOOP_EN");
        PARITY    = uvm_reg_field::type_id::create("PARITY");
        STOP_BITS = uvm_reg_field::type_id::create("STOP_BITS");
        RSVD0     = uvm_reg_field::type_id::create("RSVD0");
        RSVD1     = uvm_reg_field::type_id::create("RSVD1");
        // configure(parent, size, lsb_pos, access, volatile, reset,
        //           has_reset, is_rand, individually_accessible)
        UART_EN.configure  (this,  1,  7, "RW", 0, 1'b0,  1, 1, 0);
        TX_EN.configure    (this,  1,  6, "RW", 0, 1'b0,  1, 1, 0);
        RX_EN.configure    (this,  1,  5, "RW", 0, 1'b0,  1, 1, 0);
        LOOP_EN.configure  (this,  1,  4, "RW", 0, 1'b0,  1, 1, 0);
        PARITY.configure   (this,  2,  2, "RW", 0, 2'b00, 1, 1, 0);
        STOP_BITS.configure(this,  1,  1, "RW", 0, 1'b0,  1, 1, 0);
        RSVD0.configure    (this,  1,  0, "RO", 0, 1'b0,  1, 0, 0);
        RSVD1.configure    (this, 24,  8, "RO", 0, 24'b0, 1, 0, 0);
    endfunction
endclass

// ── STATUS (0x04) — RO ────────────────────────────────────────────────────────
class balu_status_reg extends uvm_reg;
    uvm_reg_field RSVD1;
    uvm_reg_field TIMEOUT_FLAG;
    uvm_reg_field IRQ_PENDING;
    uvm_reg_field TX_FULL;
    uvm_reg_field TX_EMPTY;
    uvm_reg_field RX_FULL;
    uvm_reg_field RX_EMPTY;
    uvm_reg_field TX_BUSY;
    uvm_reg_field RX_BUSY;
    uvm_reg_field PARITY_ERR;
    uvm_reg_field FRAME_ERR;
    uvm_reg_field OVERRUN;
    uvm_reg_field RSVD0;

    `uvm_object_utils(balu_status_reg)
    function new(string name = "balu_status_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        RSVD1        = uvm_reg_field::type_id::create("RSVD1");
        TIMEOUT_FLAG = uvm_reg_field::type_id::create("TIMEOUT_FLAG");
        IRQ_PENDING  = uvm_reg_field::type_id::create("IRQ_PENDING");
        TX_FULL      = uvm_reg_field::type_id::create("TX_FULL");
        TX_EMPTY     = uvm_reg_field::type_id::create("TX_EMPTY");
        RX_FULL      = uvm_reg_field::type_id::create("RX_FULL");
        RX_EMPTY     = uvm_reg_field::type_id::create("RX_EMPTY");
        TX_BUSY      = uvm_reg_field::type_id::create("TX_BUSY");
        RX_BUSY      = uvm_reg_field::type_id::create("RX_BUSY");
        PARITY_ERR   = uvm_reg_field::type_id::create("PARITY_ERR");
        FRAME_ERR    = uvm_reg_field::type_id::create("FRAME_ERR");
        OVERRUN      = uvm_reg_field::type_id::create("OVERRUN");
        RSVD0        = uvm_reg_field::type_id::create("RSVD0");
        RSVD1.configure      (this, 20, 12, "RO", 0, 20'b0, 1, 0, 0);
        TIMEOUT_FLAG.configure(this, 1, 11, "RO", 1, 1'b0,  1, 0, 0);
        IRQ_PENDING.configure (this, 1, 10, "RO", 1, 1'b0,  1, 0, 0);
        TX_FULL.configure     (this, 1,  9, "RO", 1, 1'b0,  1, 0, 0);
        TX_EMPTY.configure    (this, 1,  8, "RO", 1, 1'b1,  1, 0, 0);
        RX_FULL.configure     (this, 1,  7, "RO", 1, 1'b0,  1, 0, 0);
        RX_EMPTY.configure    (this, 1,  6, "RO", 1, 1'b1,  1, 0, 0);
        TX_BUSY.configure     (this, 1,  5, "RO", 1, 1'b0,  1, 0, 0);
        RX_BUSY.configure     (this, 1,  4, "RO", 1, 1'b0,  1, 0, 0);
        PARITY_ERR.configure  (this, 1,  3, "RO", 1, 1'b0,  1, 0, 0);
        FRAME_ERR.configure   (this, 1,  2, "RO", 1, 1'b0,  1, 0, 0);
        OVERRUN.configure     (this, 1,  1, "RO", 1, 1'b0,  1, 0, 0);
        RSVD0.configure       (this, 1,  0, "RO", 0, 1'b0,  1, 0, 0);
    endfunction
endclass

// ── BAUD_TUNING (0x08) — RW ──────────────────────────────────────────────────
class balu_baud_tuning_reg extends uvm_reg;
    uvm_reg_field NCO_WORD;

    `uvm_object_utils(balu_baud_tuning_reg)
    function new(string name = "balu_baud_tuning_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        NCO_WORD = uvm_reg_field::type_id::create("NCO_WORD");
        NCO_WORD.configure(this, 32, 0, "RW", 0, 32'h0, 1, 1, 0);
    endfunction
endclass

// ── FIFO_CTRL (0x0C) — RW ────────────────────────────────────────────────────
class balu_fifo_ctrl_reg extends uvm_reg;
    uvm_reg_field TX_THRESH;
    uvm_reg_field RX_THRESH;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_fifo_ctrl_reg)
    function new(string name = "balu_fifo_ctrl_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TX_THRESH = uvm_reg_field::type_id::create("TX_THRESH");
        RX_THRESH = uvm_reg_field::type_id::create("RX_THRESH");
        RESERVED  = uvm_reg_field::type_id::create("RESERVED");
        TX_THRESH.configure(this,  8,  8, "RW", 0, 8'h8,  1, 1, 0);
        RX_THRESH.configure(this,  8,  0, "RW", 0, 8'h8,  1, 1, 0);
        RESERVED.configure (this, 16, 16, "RO", 0, 16'h0, 1, 0, 0);
    endfunction
endclass

// ── FIFO_STATUS (0x10) — RO ───────────────────────────────────────────────────
class balu_fifo_status_reg extends uvm_reg;
    uvm_reg_field TX_LEVEL;
    uvm_reg_field RX_LEVEL;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_fifo_status_reg)
    function new(string name = "balu_fifo_status_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TX_LEVEL = uvm_reg_field::type_id::create("TX_LEVEL");
        RX_LEVEL = uvm_reg_field::type_id::create("RX_LEVEL");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        TX_LEVEL.configure(this,  8,  8, "RO", 1, 8'h0,  1, 0, 0);
        RX_LEVEL.configure(this,  8,  0, "RO", 1, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 16, 16, "RO", 0, 16'h0, 1, 0, 0);
    endfunction
endclass

// ── TIMEOUT_VAL (0x14) — RW ───────────────────────────────────────────────────
class balu_timeout_val_reg extends uvm_reg;
    uvm_reg_field TO_VAL;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_timeout_val_reg)
    function new(string name = "balu_timeout_val_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        TO_VAL   = uvm_reg_field::type_id::create("TO_VAL");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        TO_VAL.configure  (this, 16,  0, "RW", 0, 16'h0, 1, 1, 0);
        RESERVED.configure(this, 16, 16, "RO", 0, 16'h0, 1, 0, 0);
    endfunction
endclass

// ── INT_ENABLE (0x18) — RW ────────────────────────────────────────────────────
// Bit mapping mirrors INT_STATUS: [7]=TIMEOUT [6]=TX_THRESH [5]=RX_THRESH
//   [4]=TX_EMPTY [3]=RX_FULL [2]=PARITY_ERR [1]=FRAME_ERR [0]=OVERRUN
class balu_int_enable_reg extends uvm_reg;
    uvm_reg_field IE_BITS;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_int_enable_reg)
    function new(string name = "balu_int_enable_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        IE_BITS  = uvm_reg_field::type_id::create("IE_BITS");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        IE_BITS.configure (this,  8, 0, "RW", 0, 8'h0,  1, 1, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── INT_STATUS (0x1C) — RO (sticky; cleared via INT_CLEAR) ───────────────────
// Bit mapping: [7]=TIMEOUT [6]=TX_THRESH [5]=RX_THRESH [4]=TX_EMPTY
//              [3]=RX_FULL [2]=PARITY_ERR [1]=FRAME_ERR [0]=OVERRUN
class balu_int_status_reg extends uvm_reg;
    uvm_reg_field IS_BITS;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_int_status_reg)
    function new(string name = "balu_int_status_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        IS_BITS  = uvm_reg_field::type_id::create("IS_BITS");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        IS_BITS.configure (this,  8, 0, "RO", 1, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── INT_CLEAR (0x20) — WO (write 1 to clear INT_STATUS bits) ─────────────────
// Reading returns 0.
class balu_int_clear_reg extends uvm_reg;
    uvm_reg_field CLR_BITS;
    uvm_reg_field RESERVED;

    `uvm_object_utils(balu_int_clear_reg)
    function new(string name = "balu_int_clear_reg");
        super.new(name, 32, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        CLR_BITS = uvm_reg_field::type_id::create("CLR_BITS");
        RESERVED = uvm_reg_field::type_id::create("RESERVED");
        CLR_BITS.configure(this,  8, 0, "WO", 0, 8'h0,  1, 0, 0);
        RESERVED.configure(this, 24, 8, "RO", 0, 24'h0, 1, 0, 0);
    endfunction
endclass

// ── SCRATCH (0x24) — RW ───────────────────────────────────────────────────────
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

// ── TX_DATA (0x28) — WO ───────────────────────────────────────────────────────
// Reads return 0 (RTL case returns (others => '0') for this address).
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

// ── RX_DATA (0x2C) — RO (reading pops RX FIFO) ───────────────────────────────
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

// ── Top-level register block ──────────────────────────────────────────────────
class balu_reg_model extends uvm_reg_block;

    `uvm_object_utils(balu_reg_model)

    rand balu_ctrl_reg        CTRL;
    rand balu_status_reg      STATUS;
    rand balu_baud_tuning_reg BAUD_TUNING;
    rand balu_fifo_ctrl_reg   FIFO_CTRL;
    rand balu_fifo_status_reg FIFO_STATUS;
    rand balu_timeout_val_reg TIMEOUT_VAL;
    rand balu_int_enable_reg  INT_ENABLE;
    rand balu_int_status_reg  INT_STATUS;
    rand balu_int_clear_reg   INT_CLEAR;
    rand balu_scratch_reg     SCRATCH;
    rand balu_tx_data_reg     TX_DATA;
    rand balu_rx_data_reg     RX_DATA;

    uvm_reg_map default_map;

    function new(string name = "balu_reg_model");
        super.new(name, UVM_NO_COVERAGE);
    endfunction

    virtual function void build();
        CTRL = balu_ctrl_reg::type_id::create("CTRL");
        CTRL.build(); CTRL.configure(this, null, "");

        STATUS = balu_status_reg::type_id::create("STATUS");
        STATUS.build(); STATUS.configure(this, null, "");

        BAUD_TUNING = balu_baud_tuning_reg::type_id::create("BAUD_TUNING");
        BAUD_TUNING.build(); BAUD_TUNING.configure(this, null, "");

        FIFO_CTRL = balu_fifo_ctrl_reg::type_id::create("FIFO_CTRL");
        FIFO_CTRL.build(); FIFO_CTRL.configure(this, null, "");

        FIFO_STATUS = balu_fifo_status_reg::type_id::create("FIFO_STATUS");
        FIFO_STATUS.build(); FIFO_STATUS.configure(this, null, "");

        TIMEOUT_VAL = balu_timeout_val_reg::type_id::create("TIMEOUT_VAL");
        TIMEOUT_VAL.build(); TIMEOUT_VAL.configure(this, null, "");

        INT_ENABLE = balu_int_enable_reg::type_id::create("INT_ENABLE");
        INT_ENABLE.build(); INT_ENABLE.configure(this, null, "");

        INT_STATUS = balu_int_status_reg::type_id::create("INT_STATUS");
        INT_STATUS.build(); INT_STATUS.configure(this, null, "");

        INT_CLEAR = balu_int_clear_reg::type_id::create("INT_CLEAR");
        INT_CLEAR.build(); INT_CLEAR.configure(this, null, "");

        SCRATCH = balu_scratch_reg::type_id::create("SCRATCH");
        SCRATCH.build(); SCRATCH.configure(this, null, "");

        TX_DATA = balu_tx_data_reg::type_id::create("TX_DATA");
        TX_DATA.build(); TX_DATA.configure(this, null, "");

        RX_DATA = balu_rx_data_reg::type_id::create("RX_DATA");
        RX_DATA.build(); RX_DATA.configure(this, null, "");

        default_map = create_map("default_map", 0, 4, UVM_LITTLE_ENDIAN);
        default_map.add_reg(CTRL,        32'h00, "RW");
        default_map.add_reg(STATUS,      32'h04, "RO");
        default_map.add_reg(BAUD_TUNING, 32'h08, "RW");
        default_map.add_reg(FIFO_CTRL,   32'h0C, "RW");
        default_map.add_reg(FIFO_STATUS, 32'h10, "RO");
        default_map.add_reg(TIMEOUT_VAL, 32'h14, "RW");
        default_map.add_reg(INT_ENABLE,  32'h18, "RW");
        default_map.add_reg(INT_STATUS,  32'h1C, "RO");
        default_map.add_reg(INT_CLEAR,   32'h20, "WO");
        default_map.add_reg(SCRATCH,     32'h24, "RW");
        default_map.add_reg(TX_DATA,     32'h28, "WO");
        default_map.add_reg(RX_DATA,     32'h2C, "RO");

        lock_model();
    endfunction

endclass
