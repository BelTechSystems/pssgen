// =============================================================
// File       : buffered_axi_lite_uart.sv
// Project    : pssgen Example IP — Buffered AXI-Lite UART
// Brief      : AXI-Lite slave UART with NCO baud generator,
//              16-deep TX/RX FIFOs, and 8 interrupt sources.
// Document   : BALU-RS-001 Rev 0.4
// Standard   : IEEE 1800-2017 (SystemVerilog 2017)
//
// Functional blocks and always_ff blocks:
//   PARAM_CHECK    : Elaboration-time parameter assertions
//   NCO_BAUD       : NCO_ACCUM_p — NCO accumulator, baud pulse
//   AXI_WRITE_CTRL : AXI_AW_LATCH_p, AXI_W_LATCH_p,
//                    AXI_WRITE_RESP_p — AXI-Lite write channel
//   AXI_READ_CTRL  : AXI_READ_p — AXI-Lite read channel
//   REG_BLOCK      : REG_WRITE_p — register file
//   TX_FIFO        : TX_FIFO_p — transmit FIFO
//   RX_FIFO        : RX_FIFO_p — receive FIFO
//   TX_ENGINE      : TX_ENGINE_p — UART transmit shift register
//   RX_ENGINE      : RX_ENGINE_p — UART receive shift register
//   INT_CTRL       : INT_CTRL_p — interrupt sticky flags, IRQ
//   TIMEOUT_CTRL   : TIMEOUT_p — receive timeout counter
//   STATUS_MUX     : STATUS_p — combinatorial STATUS register
//
// Dependencies:
//   None — no imports or packages required
//
// History:
//   2026-04-08  S. Belton  Initial module + stub (IEEE 1800-2017)
// =============================================================

module buffered_axi_lite_uart #(
  parameter int P_CLK_FREQ_HZ     = 100_000_000,
  parameter int P_DEFAULT_BAUD    = 115_200,
  parameter int P_FIFO_DEPTH      = 16,
  parameter int P_TIMEOUT_DEFAULT = 255
)(
  // -- Group 1: System ----------------------------------------
  input  logic        axi_aclk,
  input  logic        axi_aresetn,    // synchronous active-low reset

  // -- Group 2: AXI-Lite Write Address Channel ----------------
  input  logic        s_axi_awvalid,
  output logic        s_axi_awready,
  input  logic [7:0]  s_axi_awaddr,   // 8-bit covers 0x00-0xFF
  input  logic [2:0]  s_axi_awprot,   // accepted, not decoded

  // -- Group 3: AXI-Lite Write Data Channel -------------------
  input  logic        s_axi_wvalid,
  output logic        s_axi_wready,
  input  logic [31:0] s_axi_wdata,
  input  logic [3:0]  s_axi_wstrb,    // byte enables

  // -- Group 4: AXI-Lite Write Response Channel ---------------
  output logic        s_axi_bvalid,
  input  logic        s_axi_bready,
  output logic [1:0]  s_axi_bresp,    // 00=OKAY 10=SLVERR

  // -- Group 5: AXI-Lite Read Address Channel -----------------
  input  logic        s_axi_arvalid,
  output logic        s_axi_arready,
  input  logic [7:0]  s_axi_araddr,
  input  logic [2:0]  s_axi_arprot,   // accepted, not decoded

  // -- Group 6: AXI-Lite Read Data Channel --------------------
  output logic        s_axi_rvalid,
  input  logic        s_axi_rready,
  output logic [31:0] s_axi_rdata,
  output logic [1:0]  s_axi_rresp,    // 00=OKAY 10=SLVERR

  // -- Group 7: UART Serial Interface -------------------------
  output logic        uart_tx,         // serial TX — idle high
  input  logic        uart_rx,         // serial RX — idle high

  // -- Group 8: Interrupt -------------------------------------
  output logic        irq              // active-high interrupt
);

  // ===========================================================
  // Localparams — all LP_<ALL_CAPS>_c
  // ===========================================================

  // Derived from parameters — do not override
  localparam int LP_ADDR_WIDTH_c = 8;
  localparam int LP_DATA_WIDTH_c = 32;

  // NCO reset value: round(P_DEFAULT_BAUD * 2^32 / P_CLK_FREQ_HZ)
  localparam logic [31:0] LP_BAUD_TUNING_RESET_c =
    $rtoi($itor(P_DEFAULT_BAUD) * (2.0**32) /
          $itor(P_CLK_FREQ_HZ) + 0.5);

  localparam int LP_FIFO_ADDR_WIDTH_c = $clog2(P_FIFO_DEPTH);

  localparam logic [7:0] LP_FIFO_THRESH_RESET_c =
    P_FIFO_DEPTH / 2;

  localparam logic [1:0] LP_AXI_OKAY_c   = 2'b00;
  localparam logic [1:0] LP_AXI_SLVERR_c = 2'b10;

  // Register address offsets
  localparam logic [7:0] LP_REG_CTRL_c        = 8'h00;
  localparam logic [7:0] LP_REG_STATUS_c      = 8'h04;
  localparam logic [7:0] LP_REG_BAUD_TUNING_c = 8'h08;
  localparam logic [7:0] LP_REG_FIFO_CTRL_c   = 8'h0C;
  localparam logic [7:0] LP_REG_FIFO_STATUS_c = 8'h10;
  localparam logic [7:0] LP_REG_TIMEOUT_VAL_c = 8'h14;
  localparam logic [7:0] LP_REG_INT_ENABLE_c  = 8'h18;
  localparam logic [7:0] LP_REG_INT_STATUS_c  = 8'h1C;
  localparam logic [7:0] LP_REG_INT_CLEAR_c   = 8'h20;
  localparam logic [7:0] LP_REG_SCRATCH_c     = 8'h24;
  localparam logic [7:0] LP_REG_TX_DATA_c     = 8'h28;
  localparam logic [7:0] LP_REG_RX_DATA_c     = 8'h2C;

  // ===========================================================
  // Elaboration-time assertions
  // ===========================================================

  // -- PARAM_CHECK — elaboration-time parameter assertions ----
  initial begin : PARAM_CHECK
    if (P_FIFO_DEPTH < 8 || P_FIFO_DEPTH > 256)
      $fatal(1, "buffered_axi_lite_uart: P_FIFO_DEPTH must be in range 8 to 256. Got: %0d",
             P_FIFO_DEPTH);
    if ((P_FIFO_DEPTH & (P_FIFO_DEPTH - 1)) != 0)
      $fatal(1, "buffered_axi_lite_uart: P_FIFO_DEPTH must be a power of 2. Got: %0d",
             P_FIFO_DEPTH);
    if (P_CLK_FREQ_HZ < 1_000_000 || P_CLK_FREQ_HZ > 1_000_000_000)
      $fatal(1, "buffered_axi_lite_uart: P_CLK_FREQ_HZ out of range. Got: %0d",
             P_CLK_FREQ_HZ);
    if (P_DEFAULT_BAUD < 1 || P_DEFAULT_BAUD > P_CLK_FREQ_HZ / 2)
      $fatal(1, "buffered_axi_lite_uart: P_DEFAULT_BAUD out of range. Got: %0d",
             P_DEFAULT_BAUD);
    if (P_TIMEOUT_DEFAULT < 0 || P_TIMEOUT_DEFAULT > 65535)
      $fatal(1, "buffered_axi_lite_uart: P_TIMEOUT_DEFAULT out of range. Got: %0d",
             P_TIMEOUT_DEFAULT);
  end

  // NOTE: s_axi_awprot and s_axi_arprot are accepted but not
  // decoded. This is standard AXI-Lite slave practice for
  // peripherals that do not implement security zones.
  // Vivado lint warning "Input port unconnected" for these
  // signals is expected and should be waived in the XDC.
  // No tie-off required — the AXI master drives these signals.

  // ===========================================================
  // Signal declarations — all <name>_s suffix
  // The distinction between registered and combinatorial is
  // conveyed by the process structure (always_ff vs assign),
  // not by naming.
  // ===========================================================

  // ---- AXI-Lite write channel internal state ---------------
  logic [7:0]  aw_addr_lat_s;   // latched write address
  logic        aw_valid_lat_s;  // write address latched and held
  logic [31:0] w_data_lat_s;    // latched write data
  logic [3:0]  w_strb_lat_s;    // latched write strobes
  logic        w_valid_lat_s;   // write data latched and held
  logic        bvalid_s;        // write response valid — registered
  logic [1:0]  bresp_s;         // write response code — registered

  // ---- AXI-Lite read channel internal state ----------------
  logic        arready_s;       // read address ready — registered
  logic        rvalid_s;        // read data valid — registered
  logic [31:0] rdata_s;         // read data — registered
  logic [1:0]  rresp_s;         // read response code — registered

  // ---- Register file ---------------------------------------
  logic [7:0]  ctrl_s;          // CTRL[7:0] — UART_EN, TX_EN, RX_EN, ...
  logic [31:0] baud_tuning_s;   // BAUD_TUNING — NCO accumulator addend
  logic [15:0] fifo_ctrl_s;     // FIFO_CTRL[15:8]=TX_THRESH [7:0]=RX_THRESH
  logic [15:0] timeout_val_s;   // TIMEOUT_VAL — receive timeout in baud ticks
  logic [7:0]  int_enable_s;    // INT_ENABLE — per-source enable mask
  logic [7:0]  int_status_s;    // INT_STATUS — sticky interrupt flags
  logic [31:0] scratch_s;       // SCRATCH — read/write, no hardware function

  // ---- NCO baud generator ----------------------------------
  logic [31:0] nco_accum_s;     // NCO phase accumulator — wraps on overflow
  logic        baud_pulse_s;    // single-cycle pulse at baud rate (carry-out)
  logic        baud_pulse_16x_s; // 16x baud pulse for RX mid-bit sampling

  // ---- FIFO memory -----------------------------------------
  logic [7:0] tx_fifo_mem_s [0:P_FIFO_DEPTH-1];
  logic [7:0] rx_fifo_mem_s [0:P_FIFO_DEPTH-1];

  // ---- TX FIFO pointers and flags --------------------------
  logic [LP_FIFO_ADDR_WIDTH_c:0] tx_wr_ptr_s;  // extra MSB for full/empty
  logic [LP_FIFO_ADDR_WIDTH_c:0] tx_rd_ptr_s;
  logic        tx_full_s;       // TX FIFO full (combinatorial)
  logic        tx_empty_s;      // TX FIFO empty (combinatorial)
  logic [7:0]  tx_level_s;      // TX FIFO occupancy count (combinatorial)

  // ---- RX FIFO pointers and flags --------------------------
  logic [LP_FIFO_ADDR_WIDTH_c:0] rx_wr_ptr_s;
  logic [LP_FIFO_ADDR_WIDTH_c:0] rx_rd_ptr_s;
  logic        rx_full_s;       // RX FIFO full (combinatorial)
  logic        rx_empty_s;      // RX FIFO empty (combinatorial)
  logic [7:0]  rx_level_s;      // RX FIFO occupancy count (combinatorial)

  // ---- TX engine -------------------------------------------
  logic [9:0]  tx_shift_s;      // TX shift register: {stop, data[7:0], start}
  logic [3:0]  tx_bit_cnt_s;    // TX bit counter (0 = idle)
  logic        tx_busy_s;       // TX shift register actively clocking a frame

  // ---- RX engine -------------------------------------------
  logic [7:0]  rx_shift_s;      // RX shift register (data bits only)
  logic [3:0]  rx_bit_cnt_s;    // RX bit counter (0 = idle)
  logic        rx_busy_s;       // RX shift register actively receiving
  logic [1:0]  rx_sync_s;       // two-stage synchroniser for uart_rx

  // ---- Timeout controller ----------------------------------
  logic [15:0] timeout_cnt_s;   // receive timeout counter (baud pulses)
  logic        timeout_flag_s;  // TIMEOUT_FLAG — set on expiry

  // ---- Interrupt event pulses (single-cycle sources) -------
  logic ev_tx_thresh_s;
  logic ev_rx_thresh_s;
  logic ev_tx_empty_s;
  logic ev_rx_full_s;
  logic ev_parity_err_s;
  logic ev_frame_err_s;
  logic ev_overrun_s;
  logic ev_timeout_s;

  // ===========================================================
  // Concurrent assign statements
  // ===========================================================

  // FIFO full/empty — from pointer MSBs (extra bit)
  assign tx_full_s  = (tx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c] !=
                       tx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c]) &&
                      (tx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0] ==
                       tx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0]);
  assign tx_empty_s = (tx_wr_ptr_s == tx_rd_ptr_s);
  assign rx_full_s  = (rx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c] !=
                       rx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c]) &&
                      (rx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0] ==
                       rx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0]);
  assign rx_empty_s = (rx_wr_ptr_s == rx_rd_ptr_s);

  // FIFO occupancy — pointer subtraction wraps for power-of-2 depth
  assign tx_level_s = tx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0] -
                      tx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0];
  assign rx_level_s = rx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0] -
                      rx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0];

  // NCO baud pulse stub: MSB of accumulator (carry-out when implemented)
  assign baud_pulse_s = nco_accum_s[31];

  // AXI-Lite output port assignments from internal registered signals
  assign s_axi_awready = ~aw_valid_lat_s;
  assign s_axi_wready  = ~w_valid_lat_s;
  assign s_axi_bvalid  = bvalid_s;
  assign s_axi_bresp   = bresp_s;
  assign s_axi_arready = arready_s;
  assign s_axi_rvalid  = rvalid_s;
  assign s_axi_rdata   = rdata_s;
  assign s_axi_rresp   = rresp_s;

  // IRQ — OR-reduction of enabled sticky interrupt flags
  assign irq = |(int_status_s & int_enable_s);

  // UART TX output — LSB of shift register when busy, idle high otherwise
  assign uart_tx = tx_busy_s ? tx_shift_s[0] : 1'b1;

  // ===========================================================
  // Process stubs — all synchronous to axi_aclk,
  // synchronous active-low reset (axi_aresetn).
  // No asynchronous resets.
  // ===========================================================

  // -- NCO_BAUD — NCO accumulator, baud pulse -----------------
  // Block   : NCO_BAUD
  // Purpose : NCO phase accumulator; produces baud_pulse_s on carry
  //           Reset: nco_accum_s <= LP_BAUD_TUNING_RESET_c
  //           Run:   nco_accum_s <= nco_accum_s + baud_tuning_s
  // Note    : Must also produce baud_pulse_16x_s (NCO MSB-4)
  //           for RX mid-bit sampling. 16x oversampling required
  //           for noise immunity. See UART-BR requirement group.
  always_ff @(posedge axi_aclk) begin : NCO_ACCUM_p
    if (!axi_aresetn) begin
      // nco_accum_s <= LP_BAUD_TUNING_RESET_c;
    end else begin
      // nco_accum_s <= nco_accum_s + baud_tuning_s; carry out = baud_pulse_s
    end
  end

  // -- AXI_WRITE_CTRL — write address latch -------------------
  // Block   : AXI_WRITE_CTRL
  // Purpose : Latch AXI-Lite write address when awvalid & awready
  //           Reset: aw_valid_lat_s <= 0; aw_addr_lat_s <= 0
  always_ff @(posedge axi_aclk) begin : AXI_AW_LATCH_p
    if (!axi_aresetn) begin
      // aw_valid_lat_s <= 1'b0; aw_addr_lat_s <= '0;
    end else begin
      // Capture s_axi_awaddr when handshake completes
    end
  end

  // -- AXI_WRITE_CTRL — write data latch ----------------------
  // Block   : AXI_WRITE_CTRL
  // Purpose : Latch AXI-Lite write data when wvalid & wready
  //           Reset: w_valid_lat_s <= 0; w_data_lat_s <= 0
  always_ff @(posedge axi_aclk) begin : AXI_W_LATCH_p
    if (!axi_aresetn) begin
      // w_valid_lat_s <= 1'b0; w_data_lat_s <= '0; w_strb_lat_s <= '0;
    end else begin
      // Capture s_axi_wdata/wstrb when handshake completes
    end
  end

  // -- AXI_WRITE_CTRL — write response ------------------------
  // Block   : AXI_WRITE_CTRL
  // Purpose : Decode write address, dispatch to register file,
  //           drive bvalid/bresp (OKAY or SLVERR for undefined addr)
  //           Reset: bvalid_s <= 0; bresp_s <= LP_AXI_OKAY_c
  always_ff @(posedge axi_aclk) begin : AXI_WRITE_RESP_p
    if (!axi_aresetn) begin
      // bvalid_s <= 1'b0; bresp_s <= LP_AXI_OKAY_c;
    end else begin
      // When both latches valid, dispatch write; assert bvalid_s
    end
  end

  // -- AXI_READ_CTRL — read channel ---------------------------
  // Block   : AXI_READ_CTRL
  // Purpose : Decode read address, mux register data to rdata_s,
  //           drive arready/rvalid/rresp
  //           Reset: arready_s <= 1; rvalid_s <= 0; rdata_s <= 0
  always_ff @(posedge axi_aclk) begin : AXI_READ_p
    if (!axi_aresetn) begin
      // arready_s <= 1'b1; rvalid_s <= 1'b0; rdata_s <= '0;
    end else begin
      // Accept read address; mux register file output to rdata_s
    end
  end

  // -- REG_BLOCK — register file (reset + write decode) -------
  // Block   : REG_BLOCK
  // Purpose : Apply reset values on reset; decode AXI write address
  //           and update register file otherwise.
  //           BAUD_TUNING write blocked while ctrl_s[7]=UART_EN.
  //           Single process owns all register signals.
  //           Reset: ctrl_s<=0; baud_tuning_s<=LP_BAUD_TUNING_RESET_c;
  //                  fifo_ctrl_s<={LP_FIFO_THRESH_RESET_c,LP_FIFO_THRESH_RESET_c};
  //                  timeout_val_s<=P_TIMEOUT_DEFAULT; int_enable_s<=0;
  //                  int_status_s<=0; scratch_s<=0
  always_ff @(posedge axi_aclk) begin : REG_WRITE_p
    if (!axi_aresetn) begin
      // ctrl_s <= 8'h00;
      // baud_tuning_s <= LP_BAUD_TUNING_RESET_c;
      // fifo_ctrl_s <= {LP_FIFO_THRESH_RESET_c, LP_FIFO_THRESH_RESET_c};
      // timeout_val_s <= P_TIMEOUT_DEFAULT[15:0];
      // int_enable_s <= 8'h00; int_status_s <= 8'h00; scratch_s <= '0;
    end else begin
      // Case aw_addr_lat_s: update register; INT_CLEAR uses W1C logic
    end
  end

  // -- TX_FIFO — transmit FIFO --------------------------------
  // Block   : TX_FIFO
  // Purpose : Push TX_DATA writes into tx_fifo_mem_s; pop on
  //           TX engine request when not tx_empty_s
  //           Reset: tx_wr_ptr_s <= 0; tx_rd_ptr_s <= 0
  always_ff @(posedge axi_aclk) begin : TX_FIFO_p
    if (!axi_aresetn) begin
      // tx_wr_ptr_s <= '0; tx_rd_ptr_s <= '0;
    end else begin
      // Push: increment tx_wr_ptr_s; Pop: increment tx_rd_ptr_s
    end
  end

  // -- RX_FIFO — receive FIFO ---------------------------------
  // Block   : RX_FIFO
  // Purpose : Push received bytes from RX engine; pop on RX_DATA read;
  //           set ev_overrun_s if push attempted while rx_full_s
  //           Reset: rx_wr_ptr_s <= 0; rx_rd_ptr_s <= 0
  always_ff @(posedge axi_aclk) begin : RX_FIFO_p
    if (!axi_aresetn) begin
      // rx_wr_ptr_s <= '0; rx_rd_ptr_s <= '0;
    end else begin
      // Push on RX engine valid; Pop on RX_DATA AXI read
    end
  end

  // -- TX_ENGINE — UART transmit shift register ---------------
  // Block   : TX_ENGINE
  // Purpose : Load tx_shift_s from TX FIFO, clock out start/data/stop
  //           at baud_pulse_s rate; drives uart_tx via assign
  //           Reset: tx_shift_s <= '1; tx_bit_cnt_s <= 0; tx_busy_s <= 0
  always_ff @(posedge axi_aclk) begin : TX_ENGINE_p
    if (!axi_aresetn) begin
      // tx_shift_s <= '1; tx_bit_cnt_s <= '0; tx_busy_s <= 1'b0;
    end else begin
      // On baud_pulse_s: shift right; assert tx_busy_s; ev_tx_thresh_s
    end
  end

  // -- RX_ENGINE — UART receive shift register ----------------
  // Block   : RX_ENGINE
  // Purpose : Two-stage synchronise uart_rx; detect start bit;
  //           sample data at mid-baud using baud_pulse_16x_s;
  //           push to RX FIFO on stop bit. 16x oversampling for
  //           noise immunity and phase alignment.
  //           Reset: rx_sync_s <= 2'b11; rx_busy_s <= 0; rx_bit_cnt_s <= 0
  always_ff @(posedge axi_aclk) begin : RX_ENGINE_p
    if (!axi_aresetn) begin
      // rx_sync_s <= 2'b11; rx_busy_s <= 1'b0; rx_bit_cnt_s <= '0;
    end else begin
      // Synchronise uart_rx; detect falling edge; sample at half-baud
    end
  end

  // -- INT_CTRL — interrupt controller ------------------------
  // Block   : INT_CTRL
  // Purpose : Latch event pulses into int_status_s sticky flags;
  //           clear on INT_CLEAR write (W1C); irq by assign
  //           Reset: int_status_s <= 0
  always_ff @(posedge axi_aclk) begin : INT_CTRL_p
    if (!axi_aresetn) begin
      // int_status_s <= 8'h00;
    end else begin
      // OR event pulses into sticky flags; mask with W1C clear
    end
  end

  // -- TIMEOUT_CTRL — receive timeout counter -----------------
  // Block   : TIMEOUT_CTRL
  // Purpose : Count baud pulses since last RX byte; assert ev_timeout_s
  //           when timeout_cnt_s reaches timeout_val_s; clear on RX pop
  //           Reset: timeout_cnt_s <= 0; timeout_flag_s <= 0
  always_ff @(posedge axi_aclk) begin : TIMEOUT_p
    if (!axi_aresetn) begin
      // timeout_cnt_s <= '0; timeout_flag_s <= 1'b0;
    end else begin
      // Increment on baud_pulse_s; reset on RX pop; set flag on expiry
    end
  end

  // -- STATUS_MUX — combinatorial STATUS register assembly ----
  // Block   : STATUS_MUX
  // Purpose : Combinatorial assembly of STATUS[31:0] from FIFO
  //           flags, engine busy signals, and UART error flags.
  //           Zero latency — software reads current-cycle state.
  //           No reset required — purely combinatorial.
  always_comb begin : STATUS_p
    // STATUS[31:12] reserved — read as zero
    // STATUS[11]    TIMEOUT_FLAG
    // STATUS[10]    INT_PENDING (mirrors IRQ output)
    // STATUS[9]     TX_FULL
    // STATUS[8]     TX_EMPTY
    // STATUS[7]     RX_FULL
    // STATUS[6]     RX_EMPTY
    // STATUS[5]     TX_BUSY
    // STATUS[4]     RX_BUSY
    // STATUS[3]     PARITY_ERR
    // STATUS[2]     FRAME_ERR
    // STATUS[1]     OVERRUN
    // STATUS[0]     reserved — read as zero
    rdata_s = '0; // stub: full assembly implemented with register file
  end

endmodule : buffered_axi_lite_uart
