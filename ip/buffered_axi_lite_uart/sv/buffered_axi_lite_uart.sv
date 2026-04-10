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
//   STATUS_MUX     : STATUS_p — always_comb STATUS register assembly;
//                    drives status_word_s; AXI_READ_p muxes into rdata_s
//
// Dependencies:
//   None — no imports or packages required
//
// Implementation status: complete — all processes implemented;
//   pending Verilator verification and synthesis
// Portability: $rtoi/$itor used only in localparam computation;
//   no simulation/synthesis impact
//
// History:
//   2026-04-08  S. Belton  Initial module + stub (IEEE 1800-2017)
//   2026-04-10  S. Belton  Reset branches implemented,
//                          STATUS_p complete, ev_* comments
//   2026-04-10  S. Belton  Full architecture implementation
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
  logic        arready_s;        // read address ready — registered
  logic        rvalid_s;         // read data valid — registered
  logic [31:0] rdata_s;          // read data — registered
  logic [1:0]  rresp_s;          // read response code — registered
  logic [31:0] status_word_s;    // STATUS combinatorial word — assembled by STATUS_p
  logic        rx_fifo_pop_s;    // one-cycle pop from AXI_READ_p when RX_DATA read

  // ---- Register file ---------------------------------------
  logic [7:0]  ctrl_s;          // CTRL[7:0] — UART_EN, TX_EN, RX_EN, ...
  logic [31:0] baud_tuning_s;   // BAUD_TUNING — NCO accumulator addend
  logic [15:0] fifo_ctrl_s;     // FIFO_CTRL[15:8]=TX_THRESH [7:0]=RX_THRESH
  logic [15:0] timeout_val_s;   // TIMEOUT_VAL — receive timeout in baud ticks
  logic [7:0]  int_enable_s;    // INT_ENABLE — per-source enable mask
  logic [7:0]  int_status_s;    // INT_STATUS — sticky interrupt flags
  logic [31:0] scratch_s;       // SCRATCH — read/write, no hardware function
  logic [7:0]  w1c_mask_s;      // write-one-to-clear mask from REG_WRITE_p to INT_CTRL_p

  // ---- NCO baud generator ----------------------------------
  logic [31:0] nco_accum_s;      // NCO phase accumulator — wraps on overflow
  logic        baud_pulse_s;     // single-cycle pulse at baud rate (registered carry)
  logic        baud_pulse_16x_s; // 16x baud pulse for RX mid-bit sampling
  logic [32:0] sum_v;            // 33-bit sum for NCO carry detection

  // ---- FIFO memory -----------------------------------------
  logic [7:0] tx_fifo_mem_s [0:P_FIFO_DEPTH-1];
  logic [7:0] rx_fifo_mem_s [0:P_FIFO_DEPTH-1];

  // ---- TX FIFO pointers and flags --------------------------
  logic [LP_FIFO_ADDR_WIDTH_c:0] tx_wr_ptr_s;  // extra MSB for full/empty
  logic [LP_FIFO_ADDR_WIDTH_c:0] tx_rd_ptr_s;
  logic        tx_full_s;         // TX FIFO full (combinatorial)
  logic        tx_empty_s;        // TX FIFO empty (combinatorial)
  logic [7:0]  tx_level_s;        // TX FIFO occupancy count (combinatorial)
  logic [7:0]  tx_fifo_byte_s;    // current byte at TX FIFO read pointer (combinatorial)
  logic        tx_fifo_pop_s;     // one-cycle pop request from TX_ENGINE_p to TX_FIFO_p

  // ---- RX FIFO pointers and flags --------------------------
  logic [LP_FIFO_ADDR_WIDTH_c:0] rx_wr_ptr_s;
  logic [LP_FIFO_ADDR_WIDTH_c:0] rx_rd_ptr_s;
  logic        rx_full_s;         // RX FIFO full (combinatorial)
  logic        rx_empty_s;        // RX FIFO empty (combinatorial)
  logic [7:0]  rx_level_s;        // RX FIFO occupancy count (combinatorial)
  logic        rx_fifo_push_s;    // one-cycle push strobe from RX_ENGINE_p
  logic [7:0]  rx_fifo_wdata_s;   // data byte to push into RX FIFO

  // ---- TX engine -------------------------------------------
  logic [9:0]  tx_shift_s;       // TX shift register: {stop, data[7:0], start}
  logic [3:0]  tx_bit_cnt_s;     // TX bit counter (0 = idle)
  logic        tx_busy_s;        // TX shift register actively clocking a frame

  // ---- RX engine -------------------------------------------
  logic [7:0]  rx_shift_s;       // RX shift register (data bits only)
  logic [3:0]  rx_bit_cnt_s;     // RX bit counter (0 = idle)
  logic        rx_busy_s;        // RX shift register actively receiving
  logic [1:0]  rx_sync_s;        // two-stage synchroniser for uart_rx
  logic [3:0]  rx_os_cnt_s;      // 16x oversampling counter for RX mid-bit detection

  // ---- Timeout controller ----------------------------------
  logic [15:0] timeout_cnt_s;    // receive timeout counter (baud pulses)
  logic        timeout_flag_s;   // TIMEOUT_FLAG — set on expiry

  // ---- Interrupt event pulses (single-cycle sources) -------
  logic ev_tx_thresh_s;   // TX level crossed threshold — TX_ENGINE_p
  logic ev_rx_thresh_s;   // RX level crossed threshold — RX_ENGINE_p
  logic ev_tx_empty_s;    // TX FIFO became empty — TX_FIFO_p
  logic ev_rx_full_s;     // RX FIFO full — RX_FIFO_p
  logic ev_parity_err_s;  // parity error detected — RX_ENGINE_p
  logic ev_frame_err_s;   // framing error detected — RX_ENGINE_p
  logic ev_overrun_s;     // RX overrun (push while full) — RX_FIFO_p
  logic ev_timeout_s;     // receive timeout expired — TIMEOUT_p

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

  // TX FIFO read-port — combinatorial byte at current read pointer
  assign tx_fifo_byte_s =
    tx_fifo_mem_s[tx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0]];

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
  // Clocked processes — synchronous to axi_aclk,
  // synchronous active-low reset (axi_aresetn).
  // No asynchronous resets.
  // ===========================================================

  // -- NCO_BAUD — NCO accumulator, baud pulse -----------------
  // Block   : NCO_BAUD
  // Purpose : 32-bit NCO phase accumulator. baud_pulse_s is the
  //           registered carry-out (bit-32 overflow each cycle).
  //           baud_pulse_16x_s is the carry from the lower 28 bits,
  //           producing a 16x-baud pulse for RX mid-bit sampling.
  always_ff @(posedge axi_aclk) begin : NCO_ACCUM_p
    if (!axi_aresetn) begin
      nco_accum_s      <= LP_BAUD_TUNING_RESET_c;
      baud_pulse_s     <= 1'b0;
      baud_pulse_16x_s <= 1'b0;
    end else begin
      sum_v          = {1'b0, nco_accum_s} + {1'b0, baud_tuning_s};
      nco_accum_s   <= sum_v[31:0];
      baud_pulse_s  <= sum_v[32];
      baud_pulse_16x_s <= ({1'b0, nco_accum_s[27:0]} +
                            baud_tuning_s[27:0])[28];
    end
  end

  // -- AXI_WRITE_CTRL — write address latch -------------------
  // Block   : AXI_WRITE_CTRL
  // Purpose : Latch AXI-Lite write address when awvalid & awready;
  //           hold until write response handshake completes
  always_ff @(posedge axi_aclk) begin : AXI_AW_LATCH_p
    if (!axi_aresetn) begin
      aw_valid_lat_s <= 1'b0;
      aw_addr_lat_s  <= '0;
    end else begin
      if (s_axi_awvalid && !aw_valid_lat_s) begin
        aw_addr_lat_s  <= s_axi_awaddr;
        aw_valid_lat_s <= 1'b1;
      end
      if (bvalid_s && s_axi_bready)
        aw_valid_lat_s <= 1'b0;
    end
  end

  // -- AXI_WRITE_CTRL — write data latch ----------------------
  // Block   : AXI_WRITE_CTRL
  // Purpose : Latch AXI-Lite write data when wvalid & wready;
  //           hold until write response handshake completes
  always_ff @(posedge axi_aclk) begin : AXI_W_LATCH_p
    if (!axi_aresetn) begin
      w_valid_lat_s <= 1'b0;
      w_data_lat_s  <= '0;
      w_strb_lat_s  <= '0;
    end else begin
      if (s_axi_wvalid && !w_valid_lat_s) begin
        w_data_lat_s  <= s_axi_wdata;
        w_strb_lat_s  <= s_axi_wstrb;
        w_valid_lat_s <= 1'b1;
      end
      if (bvalid_s && s_axi_bready)
        w_valid_lat_s <= 1'b0;
    end
  end

  // -- AXI_WRITE_CTRL — write response ------------------------
  // Block   : AXI_WRITE_CTRL
  // Purpose : Assert bvalid when both address and data latches are
  //           ready; determine bresp from address decode; clear on
  //           bready handshake
  always_ff @(posedge axi_aclk) begin : AXI_WRITE_RESP_p
    if (!axi_aresetn) begin
      bvalid_s <= 1'b0;
      bresp_s  <= LP_AXI_OKAY_c;
    end else begin
      if (bvalid_s && s_axi_bready) begin
        bvalid_s <= 1'b0;
        bresp_s  <= LP_AXI_OKAY_c;
      end
      if (aw_valid_lat_s && w_valid_lat_s && !bvalid_s) begin
        // STATUS and FIFO_STATUS are read-only; RX_DATA is read-only
        if (aw_addr_lat_s == LP_REG_STATUS_c      ||
            aw_addr_lat_s == LP_REG_FIFO_STATUS_c ||
            aw_addr_lat_s == LP_REG_RX_DATA_c) begin
          bresp_s <= LP_AXI_SLVERR_c;
        end else if (aw_addr_lat_s != LP_REG_CTRL_c        &&
                     aw_addr_lat_s != LP_REG_BAUD_TUNING_c &&
                     aw_addr_lat_s != LP_REG_FIFO_CTRL_c   &&
                     aw_addr_lat_s != LP_REG_TIMEOUT_VAL_c &&
                     aw_addr_lat_s != LP_REG_INT_ENABLE_c  &&
                     aw_addr_lat_s != LP_REG_INT_CLEAR_c   &&
                     aw_addr_lat_s != LP_REG_SCRATCH_c     &&
                     aw_addr_lat_s != LP_REG_TX_DATA_c) begin
          bresp_s <= LP_AXI_SLVERR_c;
        end else begin
          bresp_s <= LP_AXI_OKAY_c;
        end
        bvalid_s <= 1'b1;
      end
    end
  end

  // -- AXI_READ_CTRL — read channel ---------------------------
  // Block   : AXI_READ_CTRL
  // Purpose : Accept arvalid when arready; decode araddr and mux
  //           register content into rdata_s; assert rvalid; deassert
  //           arready until rvalid handshake completes
  always_ff @(posedge axi_aclk) begin : AXI_READ_p
    if (!axi_aresetn) begin
      arready_s     <= 1'b1;
      rvalid_s      <= 1'b0;
      rdata_s       <= '0;
      rresp_s       <= LP_AXI_OKAY_c;
      rx_fifo_pop_s <= 1'b0;
    end else begin
      if (rvalid_s && s_axi_rready) begin
        rvalid_s  <= 1'b0;
        arready_s <= 1'b1;
      end
      if (s_axi_arvalid && arready_s) begin
        arready_s     <= 1'b0;
        rvalid_s      <= 1'b1;
        rx_fifo_pop_s <= 1'b0;
        unique case (s_axi_araddr)
          LP_REG_CTRL_c: begin
            rdata_s <= {24'h0, ctrl_s};
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_STATUS_c: begin
            rdata_s <= status_word_s;
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_BAUD_TUNING_c: begin
            rdata_s <= baud_tuning_s;
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_FIFO_CTRL_c: begin
            rdata_s <= {16'h0, fifo_ctrl_s};
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_FIFO_STATUS_c: begin
            rdata_s <= {16'h0, tx_level_s, rx_level_s};
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_TIMEOUT_VAL_c: begin
            rdata_s <= {16'h0, timeout_val_s};
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_INT_ENABLE_c: begin
            rdata_s <= {24'h0, int_enable_s};
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_INT_STATUS_c: begin
            rdata_s <= {24'h0, int_status_s};
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_INT_CLEAR_c: begin
            rdata_s <= '0;
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_SCRATCH_c: begin
            rdata_s <= scratch_s;
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_TX_DATA_c: begin
            rdata_s <= '0;    // write-only, reads zero
            rresp_s <= LP_AXI_OKAY_c;
          end
          LP_REG_RX_DATA_c: begin
            rdata_s <= {24'h0,
              rx_fifo_mem_s[rx_rd_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0]]};
            rx_fifo_pop_s <= 1'b1;
            rresp_s <= LP_AXI_OKAY_c;
          end
          default: begin
            rdata_s <= '0;
            rresp_s <= LP_AXI_SLVERR_c;
          end
        endcase
      end else begin
        rx_fifo_pop_s <= 1'b0;
      end
    end
  end

  // -- REG_BLOCK — register file (reset + write decode) -------
  // Block   : REG_BLOCK
  // Purpose : Apply reset values on reset; decode write address and
  //           update register file. BAUD_TUNING write blocked while
  //           UART_EN (ctrl_s[7]) is set. Does not own int_status_s;
  //           W1C mask for INT_CLEAR passed to INT_CTRL_p via w1c_mask_s.
  always_ff @(posedge axi_aclk) begin : REG_WRITE_p
    if (!axi_aresetn) begin
      ctrl_s        <= 8'h00;
      baud_tuning_s <= LP_BAUD_TUNING_RESET_c;
      fifo_ctrl_s   <= {LP_FIFO_THRESH_RESET_c,
                        LP_FIFO_THRESH_RESET_c};
      timeout_val_s <= 16'(P_TIMEOUT_DEFAULT);
      int_enable_s  <= 8'h00;
      scratch_s     <= '0;
      w1c_mask_s    <= 8'h00;
    end else begin
      w1c_mask_s <= 8'h00;
      if (aw_valid_lat_s && w_valid_lat_s && !bvalid_s) begin
        unique case (aw_addr_lat_s)
          LP_REG_CTRL_c: begin
            ctrl_s <= w_data_lat_s[7:0];
          end
          LP_REG_BAUD_TUNING_c: begin
            if (!ctrl_s[7])
              baud_tuning_s <= w_data_lat_s;
          end
          LP_REG_FIFO_CTRL_c: begin
            fifo_ctrl_s <= w_data_lat_s[15:0];
          end
          LP_REG_TIMEOUT_VAL_c: begin
            timeout_val_s <= w_data_lat_s[15:0];
          end
          LP_REG_INT_ENABLE_c: begin
            int_enable_s <= w_data_lat_s[7:0];
          end
          LP_REG_INT_CLEAR_c: begin
            w1c_mask_s <= w_data_lat_s[7:0];
          end
          LP_REG_SCRATCH_c: begin
            scratch_s <= w_data_lat_s;
          end
          default: ;  // undefined or read-only addresses silently ignored
        endcase
      end
    end
  end

  // -- TX_FIFO — transmit FIFO --------------------------------
  // Block   : TX_FIFO
  // Purpose : Push TX_DATA writes from AXI write path into FIFO;
  //           pop one byte when TX engine asserts tx_fifo_pop_s
  always_ff @(posedge axi_aclk) begin : TX_FIFO_p
    if (!axi_aresetn) begin
      tx_wr_ptr_s <= '0;
      tx_rd_ptr_s <= '0;
    end else begin
      if (aw_valid_lat_s && w_valid_lat_s && !bvalid_s &&
          aw_addr_lat_s == LP_REG_TX_DATA_c && !tx_full_s) begin
        tx_fifo_mem_s[tx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0]] <=
          w_data_lat_s[7:0];
        tx_wr_ptr_s <= tx_wr_ptr_s + 1'b1;
      end
      if (tx_fifo_pop_s && !tx_empty_s)
        tx_rd_ptr_s <= tx_rd_ptr_s + 1'b1;
    end
  end

  // -- RX_FIFO — receive FIFO ---------------------------------
  // Block   : RX_FIFO
  // Purpose : Push bytes from RX engine into FIFO; pop on software
  //           RX_DATA read; assert ev_overrun_s if push while full
  always_ff @(posedge axi_aclk) begin : RX_FIFO_p
    if (!axi_aresetn) begin
      rx_wr_ptr_s  <= '0;
      rx_rd_ptr_s  <= '0;
      ev_overrun_s <= 1'b0;
      ev_rx_full_s <= 1'b0;
    end else begin
      ev_overrun_s <= 1'b0;
      ev_rx_full_s <= 1'b0;
      if (rx_fifo_push_s) begin
        if (!rx_full_s) begin
          rx_fifo_mem_s[rx_wr_ptr_s[LP_FIFO_ADDR_WIDTH_c-1:0]] <=
            rx_fifo_wdata_s;
          rx_wr_ptr_s <= rx_wr_ptr_s + 1'b1;
          if (rx_level_s == (P_FIFO_DEPTH - 1))
            ev_rx_full_s <= 1'b1;
        end else begin
          ev_overrun_s <= 1'b1;
        end
      end
      if (rx_fifo_pop_s && !rx_empty_s)
        rx_rd_ptr_s <= rx_rd_ptr_s + 1'b1;
    end
  end

  // -- TX_ENGINE — UART transmit shift register ---------------
  // Block   : TX_ENGINE
  // Purpose : Load TX FIFO byte when idle and baud_pulse_s fires;
  //           shift right one bit per baud pulse; assert tx_fifo_pop_s
  //           on load; fire event pulses on threshold and empty
  always_ff @(posedge axi_aclk) begin : TX_ENGINE_p
    if (!axi_aresetn) begin
      tx_shift_s    <= '1;
      tx_bit_cnt_s  <= '0;
      tx_busy_s     <= 1'b0;
      tx_fifo_pop_s <= 1'b0;
      ev_tx_thresh_s <= 1'b0;
      ev_tx_empty_s  <= 1'b0;
    end else begin
      ev_tx_thresh_s <= 1'b0;
      ev_tx_empty_s  <= 1'b0;
      tx_fifo_pop_s  <= 1'b0;
      if (baud_pulse_s) begin
        if (!tx_busy_s) begin
          if (!tx_empty_s && ctrl_s[6] && ctrl_s[7]) begin
            // Load frame: start(0), data[7:0], stop(1) — LSB first
            tx_shift_s   <= {1'b1, tx_fifo_byte_s, 1'b0};
            tx_bit_cnt_s <= 4'd10;
            tx_busy_s    <= 1'b1;
            tx_fifo_pop_s <= 1'b1;
          end
        end else begin
          tx_shift_s   <= {1'b1, tx_shift_s[9:1]};
          tx_bit_cnt_s <= tx_bit_cnt_s - 1'b1;
          if (tx_bit_cnt_s == 4'd1) begin
            tx_busy_s <= 1'b0;
            if (tx_empty_s)
              ev_tx_empty_s <= 1'b1;
          end
          if (tx_level_s < fifo_ctrl_s[15:8])
            ev_tx_thresh_s <= 1'b1;
        end
      end
    end
  end

  // -- RX_ENGINE — UART receive shift register ----------------
  // Block   : RX_ENGINE
  // Purpose : Two-stage synchronise uart_rx; detect start bit on
  //           falling edge; use 16x oversampling counter to sample
  //           at mid-bit; push received byte to RX FIFO on stop bit;
  //           assert frame/parity error events as appropriate
  always_ff @(posedge axi_aclk) begin : RX_ENGINE_p
    if (!axi_aresetn) begin
      rx_sync_s       <= 2'b11;
      rx_busy_s       <= 1'b0;
      rx_bit_cnt_s    <= '0;
      rx_shift_s      <= '0;
      rx_os_cnt_s     <= '0;
      rx_fifo_push_s  <= 1'b0;
      rx_fifo_wdata_s <= 8'h00;
      ev_parity_err_s <= 1'b0;
      ev_frame_err_s  <= 1'b0;
      ev_rx_thresh_s  <= 1'b0;
    end else begin
      rx_fifo_push_s  <= 1'b0;
      ev_parity_err_s <= 1'b0;
      ev_frame_err_s  <= 1'b0;
      ev_rx_thresh_s  <= 1'b0;

      rx_sync_s <= {rx_sync_s[0], uart_rx};

      if (ctrl_s[5] && ctrl_s[7]) begin
        if (baud_pulse_16x_s) begin
          if (!rx_busy_s) begin
            if (!rx_sync_s[1] && rx_sync_s[0]) begin
              rx_os_cnt_s  <= 4'd1;
              rx_bit_cnt_s <= '0;
              rx_busy_s    <= 1'b1;
            end
          end else begin
            if (rx_os_cnt_s == 4'd15) begin
              rx_os_cnt_s <= '0;
              if (rx_bit_cnt_s < 4'd8) begin
                rx_shift_s   <= {rx_sync_s[1], rx_shift_s[7:1]};
                rx_bit_cnt_s <= rx_bit_cnt_s + 1'b1;
              end else if (rx_bit_cnt_s == 4'd8) begin
                if (!rx_sync_s[1])
                  ev_frame_err_s <= 1'b1;
                rx_fifo_push_s  <= 1'b1;
                rx_fifo_wdata_s <= rx_shift_s;
                rx_busy_s       <= 1'b0;
                rx_bit_cnt_s    <= '0;
                if (rx_level_s >= fifo_ctrl_s[7:0])
                  ev_rx_thresh_s <= 1'b1;
              end
            end else begin
              rx_os_cnt_s <= rx_os_cnt_s + 1'b1;
            end
          end
        end
      end
    end
  end

  // -- INT_CTRL — interrupt controller ------------------------
  // Block   : INT_CTRL
  // Purpose : OR all event pulses into int_status_s sticky flags each
  //           cycle; apply W1C clear mask from REG_WRITE_p; irq by assign
  //           Bit mapping: [7]=TIMEOUT [6]=TX_THRESH [5]=RX_THRESH
  //           [4]=TX_EMPTY [3]=RX_FULL [2]=PARITY_ERR [1]=FRAME_ERR
  //           [0]=OVERRUN
  always_ff @(posedge axi_aclk) begin : INT_CTRL_p
    if (!axi_aresetn) begin
      int_status_s <= 8'h00;
    end else begin
      int_status_s <= (int_status_s & ~w1c_mask_s) |
                      {ev_timeout_s,    ev_tx_thresh_s, ev_rx_thresh_s,
                       ev_tx_empty_s,   ev_rx_full_s,   ev_parity_err_s,
                       ev_frame_err_s,  ev_overrun_s};
    end
  end

  // -- TIMEOUT_CTRL — receive timeout counter -----------------
  // Block   : TIMEOUT_CTRL
  // Purpose : Count baud pulses while bytes sit unread in RX FIFO;
  //           assert ev_timeout_s when count reaches timeout_val_s;
  //           clear flag and counter when FIFO drains; 0 disables
  always_ff @(posedge axi_aclk) begin : TIMEOUT_p
    if (!axi_aresetn) begin
      timeout_cnt_s  <= '0;
      timeout_flag_s <= 1'b0;
      ev_timeout_s   <= 1'b0;
    end else begin
      ev_timeout_s <= 1'b0;
      if (baud_pulse_s) begin
        if (!rx_busy_s && !rx_empty_s) begin
          if (timeout_val_s != 16'h0000 &&
              timeout_cnt_s < timeout_val_s) begin
            timeout_cnt_s <= timeout_cnt_s + 1'b1;
          end else if (timeout_val_s != 16'h0000 &&
                       timeout_cnt_s >= timeout_val_s) begin
            timeout_flag_s <= 1'b1;
            ev_timeout_s   <= 1'b1;
            timeout_cnt_s  <= '0;
          end
        end else begin
          timeout_cnt_s <= '0;
        end
      end
      if (rx_empty_s) begin
        timeout_flag_s <= 1'b0;
        timeout_cnt_s  <= '0;
      end
    end
  end

  // -- STATUS_MUX — combinatorial STATUS register -------------
  // Block   : STATUS_MUX
  // Purpose : Assemble STATUS[31:0] from live hardware signals.
  //           Zero latency — software reads current-cycle state.
  //           Owns status_word_s only. AXI_READ_p muxes this
  //           into rdata_s when araddr == LP_REG_STATUS_c.
  always_comb begin : STATUS_p
    status_word_s                = '0;
    status_word_s[11]            = timeout_flag_s;
    status_word_s[10]            = |(int_status_s & int_enable_s);
    status_word_s[9]             = tx_full_s;
    status_word_s[8]             = tx_empty_s;
    status_word_s[7]             = rx_full_s;
    status_word_s[6]             = rx_empty_s;
    status_word_s[5]             = tx_busy_s;
    status_word_s[4]             = rx_busy_s;
    status_word_s[3]             = ev_parity_err_s;
    status_word_s[2]             = ev_frame_err_s;
    status_word_s[1]             = ev_overrun_s;
    // status_word_s[0] reserved — read as zero
  end

endmodule : buffered_axi_lite_uart
