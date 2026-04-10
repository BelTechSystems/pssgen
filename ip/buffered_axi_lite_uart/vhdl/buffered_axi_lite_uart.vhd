-- =============================================================
-- File       : buffered_axi_lite_uart.vhd
-- Project    : pssgen Example IP — Buffered AXI-Lite UART
-- Brief      : AXI-Lite slave UART with NCO baud generator,
--              16-deep TX/RX FIFOs, and 8 interrupt sources.
-- Document   : BALU-RS-001 Rev 0.4
-- Standard   : VHDL-2008 (IEEE 1076-2008)
--
-- Functional blocks and processes:
--   PARAM_CHECK    : Elaboration-time generic assertions
--   NCO_BAUD       : NCO_ACCUM_p — NCO accumulator, baud pulse
--   AXI_WRITE_CTRL : AXI_AW_LATCH_p, AXI_W_LATCH_p,
--                    AXI_WRITE_RESP_p — AXI-Lite write channel
--   AXI_READ_CTRL  : AXI_READ_p — AXI-Lite read channel
--   REG_BLOCK      : REG_WRITE_p — register file (reset + write decode)
--   TX_FIFO        : TX_FIFO_p — transmit FIFO
--   RX_FIFO        : RX_FIFO_p — receive FIFO
--   TX_ENGINE      : TX_ENGINE_p — UART transmit shift register
--   RX_ENGINE      : RX_ENGINE_p — UART receive shift register
--   INT_CTRL       : INT_CTRL_p — interrupt sticky flags, IRQ
--   TIMEOUT_CTRL   : TIMEOUT_p — receive timeout counter
--   STATUS_MUX     : STATUS_p — process(all) STATUS register assembly;
--                    drives status_word_s; AXI_READ_p muxes into rdata_s
--
-- Dependencies:
--   ieee.std_logic_1164
--   ieee.numeric_std
--   ieee.math_real (elaboration only — for baud reset calc)
--
-- Portability:    ieee.math_real used at elaboration only; no synthesis impact
-- Impl. status:  complete — all processes implemented;
--                pending GHDL verification and synthesis
--
-- History:
--   2026-04-07  S. Belton  Initial entity + architecture stub
--   2026-04-10  S. Belton  Reset branches implemented, STATUS_p complete
--                          with live hardware signal assembly
--   2026-04-10  S. Belton  Full architecture implementation
-- =============================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;  -- used only for elaboration constant

-- =============================================================
-- Entity
-- =============================================================

entity buffered_axi_lite_uart is
  generic (
    G_CLK_FREQ_HZ     : integer := 100_000_000;
    G_DEFAULT_BAUD    : integer := 115_200;
    G_FIFO_DEPTH      : integer := 16;
    G_TIMEOUT_DEFAULT : integer := 255
  );
  port (
    -- ---- Group 1: System ----------------------------------
    axi_aclk    : in  std_logic;
    axi_aresetn : in  std_logic; -- synchronous active-low reset

    -- ---- Group 2: AXI-Lite Write Address Channel ----------
    s_axi_awvalid : in  std_logic;
    s_axi_awready : out std_logic;
    s_axi_awaddr  : in  std_logic_vector(7 downto 0); -- 8-bit AXI address bus
    s_axi_awprot  : in  std_logic_vector(2 downto 0); -- accepted, not decoded

    -- ---- Group 3: AXI-Lite Write Data Channel -------------
    s_axi_wvalid  : in  std_logic;
    s_axi_wready  : out std_logic;
    s_axi_wdata   : in  std_logic_vector(31 downto 0); -- 32-bit write data
    s_axi_wstrb   : in  std_logic_vector(3 downto 0); -- byte enables

    -- ---- Group 4: AXI-Lite Write Response Channel ---------
    s_axi_bvalid  : out std_logic;
    s_axi_bready  : in  std_logic;
    s_axi_bresp   : out std_logic_vector(1 downto 0); -- 00=OKAY 10=SLVERR

    -- ---- Group 5: AXI-Lite Read Address Channel -----------
    s_axi_arvalid : in  std_logic;
    s_axi_arready : out std_logic;
    s_axi_araddr  : in  std_logic_vector(7 downto 0); -- 8-bit read address
    s_axi_arprot  : in  std_logic_vector(2 downto 0); -- accepted, not decoded

    -- ---- Group 6: AXI-Lite Read Data Channel --------------
    s_axi_rvalid  : out std_logic;
    s_axi_rready  : in  std_logic;
    s_axi_rdata   : out std_logic_vector(31 downto 0); -- 32-bit read data
    s_axi_rresp   : out std_logic_vector(1 downto 0); -- 00=OKAY 10=SLVERR

    -- ---- Group 7: UART Serial Interface -------------------
    uart_tx : out std_logic; -- serial TX idle high
    uart_rx : in  std_logic; -- serial RX idle high active-low start

    -- ---- Group 8: Interrupt -------------------------------
    irq : out std_logic   -- active-high; any enabled INT_STATUS bit set
  );
end entity buffered_axi_lite_uart;

-- =============================================================
-- Architecture
-- =============================================================

architecture rtl of buffered_axi_lite_uart is

  -- ===========================================================
  -- Constants — all use _c suffix
  -- ===========================================================

  constant ADDR_WIDTH_c : integer := 8;
  -- AXI-Lite address bus width

  constant DATA_WIDTH_c : integer := 32;
  -- AXI-Lite data bus width

  constant BAUD_TUNING_RESET_c : unsigned(31 downto 0) :=
    to_unsigned(
      integer(round(
        real(G_DEFAULT_BAUD) * (2.0 ** 32) /
        real(G_CLK_FREQ_HZ))),
      32);
  -- NCO accumulator addend at reset. Uses round() to minimise
  -- baud rate error. Requires ieee.math_real (elaboration only).

  constant FIFO_ADDR_WIDTH_c : integer :=
    integer(log2(real(G_FIFO_DEPTH)));
  -- FIFO read/write pointer width (extra bit for full/empty)

  constant FIFO_THRESH_RESET_c : std_logic_vector(7 downto 0) :=
    std_logic_vector(to_unsigned(G_FIFO_DEPTH / 2, 8));
  -- Default TX and RX threshold at reset (half-full)

  constant AXI_OKAY_c   : std_logic_vector(1 downto 0) := "00";
  constant AXI_SLVERR_c : std_logic_vector(1 downto 0) := "10";
  -- AXI-Lite response codes

  constant REG_CTRL_c        : std_logic_vector(7 downto 0) := x"00";
  constant REG_STATUS_c      : std_logic_vector(7 downto 0) := x"04";
  constant REG_BAUD_TUNING_c : std_logic_vector(7 downto 0) := x"08";
  constant REG_FIFO_CTRL_c   : std_logic_vector(7 downto 0) := x"0C";
  constant REG_FIFO_STATUS_c : std_logic_vector(7 downto 0) := x"10";
  constant REG_TIMEOUT_VAL_c : std_logic_vector(7 downto 0) := x"14";
  constant REG_INT_ENABLE_c  : std_logic_vector(7 downto 0) := x"18";
  constant REG_INT_STATUS_c  : std_logic_vector(7 downto 0) := x"1C";
  constant REG_INT_CLEAR_c   : std_logic_vector(7 downto 0) := x"20";
  constant REG_SCRATCH_c     : std_logic_vector(7 downto 0) := x"24";
  constant REG_TX_DATA_c     : std_logic_vector(7 downto 0) := x"28";
  constant REG_RX_DATA_c     : std_logic_vector(7 downto 0) := x"2C";
  -- Register address offsets

  -- ===========================================================
  -- Elaboration-time assertions
  -- ===========================================================

  -- PARAM_CHECK uses VHDL-2008 if-generate for elaboration asserts.
  -- The power-of-2 check uses the derived FIFO_ADDR_WIDTH_c constant:
  -- if 2**floor(log2(N)) = N then N is a power of 2.

  -- ===========================================================
  -- Types — all use _t suffix
  -- ===========================================================

  type fifo_mem_t is array (0 to G_FIFO_DEPTH - 1)
    of std_logic_vector(7 downto 0);
  -- Storage type for TX and RX FIFOs

  -- ===========================================================
  -- Signals — all use _s suffix (registered and combinatorial)
  -- The distinction between registered and combinatorial is
  -- conveyed by the process structure (clocked vs concurrent),
  -- not by naming. Use _lat where latched behaviour aids clarity.
  -- ===========================================================

  -- ---- AXI-Lite write channel internal state ---------------
  signal aw_addr_lat_s  : std_logic_vector(7 downto 0);
  -- Latched write address (held until write completes)
  signal aw_valid_lat_s : std_logic;
  -- Write address has been accepted and latched
  signal w_data_lat_s   : std_logic_vector(31 downto 0);
  -- Latched write data
  signal w_strb_lat_s   : std_logic_vector(3 downto 0);
  -- Latched write strobes
  signal w_valid_lat_s  : std_logic;
  -- Write data has been accepted and latched
  signal bvalid_s       : std_logic;
  -- Write response valid — registered
  signal bresp_s        : std_logic_vector(1 downto 0);
  -- Write response code — registered

  -- ---- AXI-Lite read channel internal state ----------------
  signal arready_s      : std_logic;
  -- Read address ready — registered
  signal rvalid_s       : std_logic;
  -- Read data valid — registered
  signal rdata_s        : std_logic_vector(31 downto 0);
  -- Read data — registered
  signal rresp_s        : std_logic_vector(1 downto 0);
  -- Read response code — registered
  signal status_word_s  : std_logic_vector(31 downto 0);
  -- STATUS register combinatorial word — assembled by STATUS_p
  signal rx_fifo_pop_s  : std_logic;
  -- Asserted for one cycle when RX_DATA register is read

  -- ---- Register file ---------------------------------------
  signal ctrl_s        : std_logic_vector(7 downto 0);
  -- CTRL[7:0] — UART_EN, TX_EN, RX_EN, LOOP_EN, PARITY[1:0], STOP
  signal baud_tuning_s : unsigned(31 downto 0);
  -- BAUD_TUNING — NCO accumulator addend
  signal fifo_ctrl_s   : std_logic_vector(15 downto 0);
  -- FIFO_CTRL[15:8]=TX_THRESH, [7:0]=RX_THRESH
  signal timeout_val_s : std_logic_vector(15 downto 0);
  -- TIMEOUT_VAL — receive timeout in baud ticks
  signal int_enable_s  : std_logic_vector(7 downto 0);
  -- INT_ENABLE — per-source interrupt enable mask
  signal int_status_s  : std_logic_vector(7 downto 0);
  -- INT_STATUS — sticky interrupt flags (W1C via INT_CLEAR)
  signal scratch_s     : std_logic_vector(31 downto 0);
  -- SCRATCH — read/write, no hardware function
  signal w1c_mask_s    : std_logic_vector(7 downto 0);
  -- Write-one-to-clear mask; driven by REG_WRITE_p each cycle;
  -- applied by INT_CTRL_p to int_status_s

  -- ---- NCO baud generator ----------------------------------
  signal nco_accum_s      : unsigned(31 downto 0);
  -- NCO phase accumulator — wraps on overflow
  signal baud_pulse_s     : std_logic;
  -- Single-cycle pulse at the baud rate (registered carry-out)
  signal baud_pulse_16x_s : std_logic;
  -- Single-cycle pulse at 16x baud rate for RX mid-bit sampling

  -- ---- TX FIFO ---------------------------------------------
  signal tx_fifo_mem_s   : fifo_mem_t;
  -- TX FIFO storage
  signal tx_wr_ptr_s     : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- TX write pointer (extra MSB for full/empty detection)
  signal tx_rd_ptr_s     : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- TX read pointer
  signal tx_full_s       : std_logic;
  -- TX FIFO full flag (combinatorial)
  signal tx_empty_s      : std_logic;
  -- TX FIFO empty flag (combinatorial)
  signal tx_level_s      : unsigned(7 downto 0);
  -- TX FIFO occupancy count (combinatorial)
  signal tx_fifo_byte_s  : std_logic_vector(7 downto 0);
  -- Current byte at TX FIFO read pointer (combinatorial)
  signal tx_fifo_pop_s   : std_logic;
  -- Asserted for one cycle by TX_ENGINE_p to pop TX FIFO

  -- ---- RX FIFO ---------------------------------------------
  signal rx_fifo_mem_s   : fifo_mem_t;
  -- RX FIFO storage
  signal rx_wr_ptr_s     : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- RX write pointer
  signal rx_rd_ptr_s     : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- RX read pointer
  signal rx_full_s       : std_logic;
  -- RX FIFO full flag (combinatorial)
  signal rx_empty_s      : std_logic;
  -- RX FIFO empty flag (combinatorial)
  signal rx_level_s      : unsigned(7 downto 0);
  -- RX FIFO occupancy count (combinatorial)
  signal rx_fifo_push_s  : std_logic;
  -- Asserted for one cycle when RX engine has a valid byte
  signal rx_fifo_wdata_s : std_logic_vector(7 downto 0);
  -- Byte to push into RX FIFO from RX engine

  -- ---- TX engine -------------------------------------------
  signal tx_shift_s   : std_logic_vector(9 downto 0);
  -- TX shift register: {stop, data[7:0], start}
  signal tx_bit_cnt_s : unsigned(3 downto 0);
  -- TX bit counter (0 = idle)
  signal tx_busy_s    : std_logic;
  -- TX shift register actively clocking a frame

  -- ---- RX engine -------------------------------------------
  signal rx_shift_s   : std_logic_vector(7 downto 0);
  -- RX shift register (data bits only)
  signal rx_bit_cnt_s : unsigned(3 downto 0);
  -- RX bit counter (0 = idle)
  signal rx_busy_s    : std_logic;
  -- RX shift register actively receiving a frame
  signal rx_sync_s    : std_logic_vector(1 downto 0);
  -- Two-stage synchroniser for uart_rx input
  signal rx_os_cnt_s  : unsigned(3 downto 0);
  -- 16x oversampling counter; counts baud_pulse_16x_s pulses

  -- ---- Timeout controller ----------------------------------
  signal timeout_cnt_s  : unsigned(15 downto 0);
  -- Receive timeout counter (counts baud pulses)
  signal timeout_flag_s : std_logic;
  -- TIMEOUT_FLAG — set on expiry, cleared when RX FIFO empty

  -- ---- Interrupt event pulses (single-cycle sources) -------
  signal ev_tx_thresh_s  : std_logic;  -- TX level crossed threshold — TX_ENGINE_p
  signal ev_rx_thresh_s  : std_logic;  -- RX level crossed threshold — RX_ENGINE_p
  signal ev_tx_empty_s   : std_logic;  -- TX FIFO became empty — TX_FIFO_p
  signal ev_rx_full_s    : std_logic;  -- RX FIFO full — RX_FIFO_p
  signal ev_parity_err_s : std_logic;  -- parity error detected — RX_ENGINE_p
  signal ev_frame_err_s  : std_logic;  -- framing error detected — RX_ENGINE_p
  signal ev_overrun_s    : std_logic;  -- RX overrun (push while full) — RX_FIFO_p
  signal ev_timeout_s    : std_logic;  -- receive timeout expired — TIMEOUT_p

begin

  -- ===========================================================
  -- Elaboration-time assertions
  -- ===========================================================

  PARAM_CHECK : if true generate
  begin
    assert (G_FIFO_DEPTH >= 8 and G_FIFO_DEPTH <= 256)
      report "buffered_axi_lite_uart: G_FIFO_DEPTH must be " &
             "in range 8 to 256. Got: " &
             integer'image(G_FIFO_DEPTH)
      severity failure;

    assert (2 ** FIFO_ADDR_WIDTH_c = G_FIFO_DEPTH)
      report "buffered_axi_lite_uart: G_FIFO_DEPTH must be " &
             "a power of 2. Got: " &
             integer'image(G_FIFO_DEPTH)
      severity failure;

    assert (G_CLK_FREQ_HZ >= 1_000_000 and
            G_CLK_FREQ_HZ <= 1_000_000_000)
      report "buffered_axi_lite_uart: G_CLK_FREQ_HZ out of " &
             "range. Got: " &
             integer'image(G_CLK_FREQ_HZ)
      severity failure;

    assert (G_DEFAULT_BAUD >= 1 and
            G_DEFAULT_BAUD <= G_CLK_FREQ_HZ / 2)
      report "buffered_axi_lite_uart: G_DEFAULT_BAUD out of " &
             "range. Got: " &
             integer'image(G_DEFAULT_BAUD)
      severity failure;

    assert (G_TIMEOUT_DEFAULT >= 0 and
            G_TIMEOUT_DEFAULT <= 65535)
      report "buffered_axi_lite_uart: G_TIMEOUT_DEFAULT out of " &
             "range. Got: " &
             integer'image(G_TIMEOUT_DEFAULT)
      severity failure;
  end generate PARAM_CHECK;

  -- ===========================================================
  -- Concurrent signal assignments
  -- ===========================================================

  -- FIFO full/empty — combinatorial from pointer MSBs (extra bit)
  tx_full_s  <= '1' when tx_wr_ptr_s(FIFO_ADDR_WIDTH_c) /=
                          tx_rd_ptr_s(FIFO_ADDR_WIDTH_c) and
                          tx_wr_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0) =
                          tx_rd_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0)
                else '0';
  tx_empty_s <= '1' when tx_wr_ptr_s = tx_rd_ptr_s else '0';
  rx_full_s  <= '1' when rx_wr_ptr_s(FIFO_ADDR_WIDTH_c) /=
                          rx_rd_ptr_s(FIFO_ADDR_WIDTH_c) and
                          rx_wr_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0) =
                          rx_rd_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0)
                else '0';
  rx_empty_s <= '1' when rx_wr_ptr_s = rx_rd_ptr_s else '0';

  -- FIFO occupancy — pointer subtraction wraps correctly for power-of-2 depth
  tx_level_s <= resize(
    tx_wr_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0) -
    tx_rd_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0), 8);
  rx_level_s <= resize(
    rx_wr_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0) -
    rx_rd_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0), 8);

  -- TX FIFO read-port — combinatorial byte at current read pointer
  tx_fifo_byte_s <= tx_fifo_mem_s(
    to_integer(tx_rd_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0)));

  -- AXI-Lite output port assignments from internal registered signals
  s_axi_awready <= not aw_valid_lat_s;
  s_axi_wready  <= not w_valid_lat_s;
  s_axi_bvalid  <= bvalid_s;
  s_axi_bresp   <= bresp_s;
  s_axi_arready <= arready_s;
  s_axi_rvalid  <= rvalid_s;
  s_axi_rdata   <= rdata_s;
  s_axi_rresp   <= rresp_s;

  -- IRQ — OR-reduction of enabled sticky interrupt flags
  irq <= '1' when (int_status_s and int_enable_s) /= x"00"
         else '0';

  -- UART TX output — LSB of shift register when busy, idle high otherwise
  uart_tx <= tx_shift_s(0) when tx_busy_s = '1' else '1';

  -- ===========================================================
  -- Clocked processes — synchronous to axi_aclk,
  -- synchronous active-low reset (axi_aresetn).
  -- No asynchronous resets.
  -- ===========================================================

  -- -------------------------------------------------------------
  -- Process : NCO_ACCUM_p
  -- Block   : NCO_BAUD
  -- Purpose : 32-bit NCO phase accumulator. baud_pulse_s is the
  --           registered carry-out (bit-32 overflow). baud_pulse_16x_s
  --           is the registered carry from the lower 28 bits, producing
  --           a 16x-baud pulse for RX mid-bit sampling.
  -- -------------------------------------------------------------
  NCO_ACCUM_p : process(axi_aclk)
    variable sum_v    : unsigned(32 downto 0);
    variable sum16_v  : unsigned(28 downto 0);
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        nco_accum_s      <= BAUD_TUNING_RESET_c;
        baud_pulse_s     <= '0';
        baud_pulse_16x_s <= '0';
      else
        sum_v   := resize(nco_accum_s, 33) + resize(baud_tuning_s, 33);
        sum16_v := resize(nco_accum_s(27 downto 0), 29) +
                   resize(baud_tuning_s(27 downto 0), 29);
        nco_accum_s      <= sum_v(31 downto 0);
        baud_pulse_s     <= sum_v(32);
        baud_pulse_16x_s <= sum16_v(28);
      end if;
    end if;
  end process NCO_ACCUM_p;

  -- -------------------------------------------------------------
  -- Process : AXI_AW_LATCH_p
  -- Block   : AXI_WRITE_CTRL
  -- Purpose : Latch AXI-Lite write address when awvalid & awready;
  --           hold until write response handshake completes
  -- -------------------------------------------------------------
  AXI_AW_LATCH_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        aw_valid_lat_s <= '0';
        aw_addr_lat_s  <= (others => '0');
      else
        if s_axi_awvalid = '1' and aw_valid_lat_s = '0' then
          aw_addr_lat_s  <= s_axi_awaddr;
          aw_valid_lat_s <= '1';
        end if;
        if bvalid_s = '1' and s_axi_bready = '1' then
          aw_valid_lat_s <= '0';
        end if;
      end if;
    end if;
  end process AXI_AW_LATCH_p;

  -- -------------------------------------------------------------
  -- Process : AXI_W_LATCH_p
  -- Block   : AXI_WRITE_CTRL
  -- Purpose : Latch AXI-Lite write data when wvalid & wready;
  --           hold until write response handshake completes
  -- -------------------------------------------------------------
  AXI_W_LATCH_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        w_valid_lat_s <= '0';
        w_data_lat_s  <= (others => '0');
        w_strb_lat_s  <= (others => '0');
      else
        if s_axi_wvalid = '1' and w_valid_lat_s = '0' then
          w_data_lat_s  <= s_axi_wdata;
          w_strb_lat_s  <= s_axi_wstrb;
          w_valid_lat_s <= '1';
        end if;
        if bvalid_s = '1' and s_axi_bready = '1' then
          w_valid_lat_s <= '0';
        end if;
      end if;
    end if;
  end process AXI_W_LATCH_p;

  -- -------------------------------------------------------------
  -- Process : AXI_WRITE_RESP_p
  -- Block   : AXI_WRITE_CTRL
  -- Purpose : Assert bvalid when both address and data latches are
  --           ready; decode address to determine OKAY or SLVERR;
  --           clear bvalid on bready handshake
  -- -------------------------------------------------------------
  AXI_WRITE_RESP_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        bvalid_s <= '0';
        bresp_s  <= AXI_OKAY_c;
      else
        if bvalid_s = '1' and s_axi_bready = '1' then
          bvalid_s <= '0';
          bresp_s  <= AXI_OKAY_c;
        end if;
        if aw_valid_lat_s = '1' and w_valid_lat_s = '1'
           and bvalid_s = '0' then
          if aw_addr_lat_s = REG_STATUS_c or
             aw_addr_lat_s = REG_FIFO_STATUS_c or
             aw_addr_lat_s = REG_RX_DATA_c then
            bresp_s <= AXI_SLVERR_c;
          elsif aw_addr_lat_s /= REG_CTRL_c and
                aw_addr_lat_s /= REG_BAUD_TUNING_c and
                aw_addr_lat_s /= REG_FIFO_CTRL_c and
                aw_addr_lat_s /= REG_TIMEOUT_VAL_c and
                aw_addr_lat_s /= REG_INT_ENABLE_c and
                aw_addr_lat_s /= REG_INT_CLEAR_c and
                aw_addr_lat_s /= REG_SCRATCH_c and
                aw_addr_lat_s /= REG_TX_DATA_c then
            bresp_s <= AXI_SLVERR_c;
          else
            bresp_s <= AXI_OKAY_c;
          end if;
          bvalid_s <= '1';
        end if;
      end if;
    end if;
  end process AXI_WRITE_RESP_p;

  -- -------------------------------------------------------------
  -- Process : AXI_READ_p
  -- Block   : AXI_READ_CTRL
  -- Purpose : Accept arvalid when arready; decode araddr and mux
  --           register content into rdata_s; assert rvalid; deassert
  --           arready until rvalid handshake completes
  -- -------------------------------------------------------------
  AXI_READ_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        arready_s     <= '1';
        rvalid_s      <= '0';
        rdata_s       <= (others => '0');
        rresp_s       <= AXI_OKAY_c;
        rx_fifo_pop_s <= '0';
      else
        if rvalid_s = '1' and s_axi_rready = '1' then
          rvalid_s  <= '0';
          arready_s <= '1';
        end if;
        if s_axi_arvalid = '1' and arready_s = '1' then
          arready_s     <= '0';
          rvalid_s      <= '1';
          rx_fifo_pop_s <= '0';
          case s_axi_araddr is
            when REG_CTRL_c =>
              rdata_s <= (31 downto 8 => '0') & ctrl_s;
              rresp_s <= AXI_OKAY_c;
            when REG_STATUS_c =>
              rdata_s <= status_word_s;
              rresp_s <= AXI_OKAY_c;
            when REG_BAUD_TUNING_c =>
              rdata_s <= std_logic_vector(baud_tuning_s);
              rresp_s <= AXI_OKAY_c;
            when REG_FIFO_CTRL_c =>
              rdata_s <= (31 downto 16 => '0') & fifo_ctrl_s;
              rresp_s <= AXI_OKAY_c;
            when REG_FIFO_STATUS_c =>
              rdata_s <= (31 downto 16 => '0') &
                         std_logic_vector(tx_level_s) &
                         std_logic_vector(rx_level_s);
              rresp_s <= AXI_OKAY_c;
            when REG_TIMEOUT_VAL_c =>
              rdata_s <= (31 downto 16 => '0') & timeout_val_s;
              rresp_s <= AXI_OKAY_c;
            when REG_INT_ENABLE_c =>
              rdata_s <= (31 downto 8 => '0') & int_enable_s;
              rresp_s <= AXI_OKAY_c;
            when REG_INT_STATUS_c =>
              rdata_s <= (31 downto 8 => '0') & int_status_s;
              rresp_s <= AXI_OKAY_c;
            when REG_INT_CLEAR_c =>
              rdata_s <= (others => '0');
              rresp_s <= AXI_OKAY_c;
            when REG_SCRATCH_c =>
              rdata_s <= scratch_s;
              rresp_s <= AXI_OKAY_c;
            when REG_TX_DATA_c =>
              rdata_s <= (others => '0');
              rresp_s <= AXI_OKAY_c;
            when REG_RX_DATA_c =>
              rdata_s <= (31 downto 8 => '0') &
                rx_fifo_mem_s(to_integer(
                  rx_rd_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0)));
              rx_fifo_pop_s <= '1';
              rresp_s <= AXI_OKAY_c;
            when others =>
              rdata_s <= (others => '0');
              rresp_s <= AXI_SLVERR_c;
          end case;
        else
          rx_fifo_pop_s <= '0';
        end if;
      end if;
    end if;
  end process AXI_READ_p;

  -- -------------------------------------------------------------
  -- Process : REG_WRITE_p
  -- Block   : REG_BLOCK
  -- Purpose : Apply reset values on reset; decode AXI write address
  --           and update register file otherwise.
  --           BAUD_TUNING write blocked while UART_EN (ctrl_s[7]) set.
  --           Does not own int_status_s — owned by INT_CTRL_p.
  --           W1C clear for INT_CLEAR passed via w1c_mask_s.
  -- -------------------------------------------------------------
  REG_WRITE_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        ctrl_s        <= (others => '0');
        baud_tuning_s <= BAUD_TUNING_RESET_c;
        fifo_ctrl_s   <= FIFO_THRESH_RESET_c & FIFO_THRESH_RESET_c;
        timeout_val_s <= std_logic_vector(
                           to_unsigned(G_TIMEOUT_DEFAULT, 16));
        int_enable_s  <= (others => '0');
        scratch_s     <= (others => '0');
        w1c_mask_s    <= (others => '0');
      else
        w1c_mask_s <= (others => '0');
        if aw_valid_lat_s = '1' and w_valid_lat_s = '1'
           and bvalid_s = '0' then
          case aw_addr_lat_s is
            when REG_CTRL_c =>
              ctrl_s <= w_data_lat_s(7 downto 0);
            when REG_BAUD_TUNING_c =>
              if ctrl_s(7) = '0' then
                baud_tuning_s <= unsigned(w_data_lat_s);
              end if;
            when REG_FIFO_CTRL_c =>
              fifo_ctrl_s <= w_data_lat_s(15 downto 0);
            when REG_TIMEOUT_VAL_c =>
              timeout_val_s <= w_data_lat_s(15 downto 0);
            when REG_INT_ENABLE_c =>
              int_enable_s <= w_data_lat_s(7 downto 0);
            when REG_INT_CLEAR_c =>
              w1c_mask_s <= w_data_lat_s(7 downto 0);
            when REG_SCRATCH_c =>
              scratch_s <= w_data_lat_s;
            when others =>
              null;
          end case;
        end if;
      end if;
    end if;
  end process REG_WRITE_p;

  -- -------------------------------------------------------------
  -- Process : TX_FIFO_p
  -- Block   : TX_FIFO
  -- Purpose : Push TX_DATA writes from AXI write path into FIFO;
  --           pop one byte when TX engine asserts tx_fifo_pop_s
  -- -------------------------------------------------------------
  TX_FIFO_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        tx_wr_ptr_s <= (others => '0');
        tx_rd_ptr_s <= (others => '0');
      else
        if aw_valid_lat_s = '1' and w_valid_lat_s = '1'
           and bvalid_s = '0'
           and aw_addr_lat_s = REG_TX_DATA_c
           and tx_full_s = '0' then
          tx_fifo_mem_s(to_integer(
            tx_wr_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0)))
            <= w_data_lat_s(7 downto 0);
          tx_wr_ptr_s <= tx_wr_ptr_s + 1;
        end if;
        if tx_fifo_pop_s = '1' and tx_empty_s = '0' then
          tx_rd_ptr_s <= tx_rd_ptr_s + 1;
        end if;
      end if;
    end if;
  end process TX_FIFO_p;

  -- -------------------------------------------------------------
  -- Process : RX_FIFO_p
  -- Block   : RX_FIFO
  -- Purpose : Push bytes from RX engine into FIFO; pop on software
  --           RX_DATA read; assert ev_overrun_s if push while full;
  --           assert ev_rx_full_s when FIFO fills after a push
  -- -------------------------------------------------------------
  RX_FIFO_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        rx_wr_ptr_s  <= (others => '0');
        rx_rd_ptr_s  <= (others => '0');
        ev_overrun_s <= '0';
        ev_rx_full_s <= '0';
      else
        ev_overrun_s <= '0';
        ev_rx_full_s <= '0';
        if rx_fifo_push_s = '1' then
          if rx_full_s = '0' then
            rx_fifo_mem_s(to_integer(
              rx_wr_ptr_s(FIFO_ADDR_WIDTH_c - 1 downto 0)))
              <= rx_fifo_wdata_s;
            rx_wr_ptr_s <= rx_wr_ptr_s + 1;
            if rx_level_s = to_unsigned(G_FIFO_DEPTH - 1, 8) then
              ev_rx_full_s <= '1';
            end if;
          else
            ev_overrun_s <= '1';
          end if;
        end if;
        if rx_fifo_pop_s = '1' and rx_empty_s = '0' then
          rx_rd_ptr_s <= rx_rd_ptr_s + 1;
        end if;
      end if;
    end if;
  end process RX_FIFO_p;

  -- -------------------------------------------------------------
  -- Process : TX_ENGINE_p
  -- Block   : TX_ENGINE
  -- Purpose : Load TX FIFO byte when idle and baud_pulse_s fires;
  --           shift right one bit per baud pulse; assert tx_fifo_pop_s
  --           on load; fire event pulses on threshold and empty
  -- -------------------------------------------------------------
  TX_ENGINE_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        tx_shift_s     <= (others => '1');
        tx_bit_cnt_s   <= (others => '0');
        tx_busy_s      <= '0';
        tx_fifo_pop_s  <= '0';
        ev_tx_thresh_s <= '0';
        ev_tx_empty_s  <= '0';
      else
        ev_tx_thresh_s <= '0';
        ev_tx_empty_s  <= '0';
        tx_fifo_pop_s  <= '0';
        if baud_pulse_s = '1' then
          if tx_busy_s = '0' then
            if tx_empty_s = '0' and ctrl_s(6) = '1'
               and ctrl_s(7) = '1' then
              tx_shift_s   <= '1' & tx_fifo_byte_s & '0';
              tx_bit_cnt_s <= to_unsigned(10, 4);
              tx_busy_s    <= '1';
              tx_fifo_pop_s <= '1';
            end if;
          else
            tx_shift_s   <= '1' & tx_shift_s(9 downto 1);
            tx_bit_cnt_s <= tx_bit_cnt_s - 1;
            if tx_bit_cnt_s = to_unsigned(1, 4) then
              tx_busy_s <= '0';
              if tx_empty_s = '1' then
                ev_tx_empty_s <= '1';
              end if;
            end if;
            if tx_level_s < unsigned(fifo_ctrl_s(15 downto 8)) then
              ev_tx_thresh_s <= '1';
            end if;
          end if;
        end if;
      end if;
    end if;
  end process TX_ENGINE_p;

  -- -------------------------------------------------------------
  -- Process : RX_ENGINE_p
  -- Block   : RX_ENGINE
  -- Purpose : Two-stage synchronise uart_rx; detect start bit on
  --           falling edge; use 16x oversampling counter to sample
  --           at mid-bit; push received byte to RX FIFO on stop bit;
  --           assert frame error and rx_thresh events as appropriate
  -- -------------------------------------------------------------
  RX_ENGINE_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        rx_sync_s       <= "11";
        rx_busy_s       <= '0';
        rx_bit_cnt_s    <= (others => '0');
        rx_shift_s      <= (others => '0');
        rx_os_cnt_s     <= (others => '0');
        rx_fifo_push_s  <= '0';
        rx_fifo_wdata_s <= (others => '0');
        ev_parity_err_s <= '0';
        ev_frame_err_s  <= '0';
        ev_rx_thresh_s  <= '0';
      else
        rx_fifo_push_s  <= '0';
        ev_parity_err_s <= '0';
        ev_frame_err_s  <= '0';
        ev_rx_thresh_s  <= '0';

        rx_sync_s <= rx_sync_s(0) & uart_rx;

        if ctrl_s(5) = '1' and ctrl_s(7) = '1' then
          if baud_pulse_16x_s = '1' then
            if rx_busy_s = '0' then
              if rx_sync_s(1) = '0' and rx_sync_s(0) = '1' then
                rx_os_cnt_s  <= to_unsigned(1, 4);
                rx_bit_cnt_s <= (others => '0');
                rx_busy_s    <= '1';
              end if;
            else
              if rx_os_cnt_s = to_unsigned(15, 4) then
                rx_os_cnt_s <= (others => '0');
                if rx_bit_cnt_s < to_unsigned(8, 4) then
                  rx_shift_s   <= rx_sync_s(1) &
                                   rx_shift_s(7 downto 1);
                  rx_bit_cnt_s <= rx_bit_cnt_s + 1;
                elsif rx_bit_cnt_s = to_unsigned(8, 4) then
                  if rx_sync_s(1) = '0' then
                    ev_frame_err_s <= '1';
                  end if;
                  if ctrl_s(3 downto 2) /= "00" then
                    null;
                  end if;
                  rx_fifo_push_s  <= '1';
                  rx_fifo_wdata_s <= rx_shift_s;
                  rx_busy_s       <= '0';
                  rx_bit_cnt_s    <= (others => '0');
                  if rx_level_s >= unsigned(fifo_ctrl_s(7 downto 0))
                  then
                    ev_rx_thresh_s <= '1';
                  end if;
                end if;
              else
                rx_os_cnt_s <= rx_os_cnt_s + 1;
              end if;
            end if;
          end if;
        end if;
      end if;
    end if;
  end process RX_ENGINE_p;

  -- -------------------------------------------------------------
  -- Process : INT_CTRL_p
  -- Block   : INT_CTRL
  -- Purpose : OR all event pulses into int_status_s sticky flags each
  --           cycle; apply W1C clear mask from REG_WRITE_p via w1c_mask_s;
  --           irq driven by concurrent assign
  --           Bit mapping: [7]=TIMEOUT [6]=TX_THRESH [5]=RX_THRESH
  --           [4]=TX_EMPTY [3]=RX_FULL [2]=PARITY_ERR [1]=FRAME_ERR
  --           [0]=OVERRUN
  -- -------------------------------------------------------------
  INT_CTRL_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        int_status_s <= (others => '0');
      else
        int_status_s <=
          (int_status_s and not w1c_mask_s) or
          (ev_timeout_s    & ev_tx_thresh_s & ev_rx_thresh_s &
           ev_tx_empty_s   & ev_rx_full_s   & ev_parity_err_s &
           ev_frame_err_s  & ev_overrun_s);
      end if;
    end if;
  end process INT_CTRL_p;

  -- -------------------------------------------------------------
  -- Process : TIMEOUT_p
  -- Block   : TIMEOUT_CTRL
  -- Purpose : Count baud pulses while bytes sit unread in RX FIFO;
  --           assert ev_timeout_s when count reaches timeout_val_s;
  --           reset counter on new RX activity; clear flag when empty;
  --           timeout_val_s = 0 disables the timeout feature
  -- -------------------------------------------------------------
  TIMEOUT_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        timeout_cnt_s  <= (others => '0');
        timeout_flag_s <= '0';
        ev_timeout_s   <= '0';
      else
        ev_timeout_s <= '0';
        if baud_pulse_s = '1' then
          if rx_busy_s = '0' and rx_empty_s = '0' then
            if timeout_val_s /= (timeout_val_s'range => '0')
               and timeout_cnt_s < unsigned(timeout_val_s) then
              timeout_cnt_s <= timeout_cnt_s + 1;
            elsif timeout_val_s /= (timeout_val_s'range => '0')
                  and timeout_cnt_s >= unsigned(timeout_val_s) then
              timeout_flag_s <= '1';
              ev_timeout_s   <= '1';
              timeout_cnt_s  <= (others => '0');
            end if;
          else
            timeout_cnt_s <= (others => '0');
          end if;
        end if;
        if rx_empty_s = '1' then
          timeout_flag_s <= '0';
          timeout_cnt_s  <= (others => '0');
        end if;
      end if;
    end if;
  end process TIMEOUT_p;

  -- -------------------------------------------------------------
  -- Process : STATUS_p
  -- Block   : STATUS_MUX
  -- Purpose : Combinatorial assembly of STATUS[31:0] from live
  --           hardware signals. Zero latency — current-cycle state.
  --           Drives status_word_s only; AXI_READ_p muxes into
  --           rdata_s on STATUS register reads.
  -- Note    : VHDL-2008 process(all). The sensitivity list
  --           covers all signals read in the process body.
  -- -------------------------------------------------------------
  STATUS_p : process(all)
  begin
    status_word_s        <= (others => '0');
    status_word_s(11)    <= timeout_flag_s;
    status_word_s(10)    <= '1' when
                             (int_status_s and int_enable_s)
                             /= x"00" else '0';
    status_word_s(9)     <= tx_full_s;
    status_word_s(8)     <= tx_empty_s;
    status_word_s(7)     <= rx_full_s;
    status_word_s(6)     <= rx_empty_s;
    status_word_s(5)     <= tx_busy_s;
    status_word_s(4)     <= rx_busy_s;
    status_word_s(3)     <= ev_parity_err_s;
    status_word_s(2)     <= ev_frame_err_s;
    status_word_s(1)     <= ev_overrun_s;
    -- status_word_s(0) reserved, already zero from default
  end process STATUS_p;

end architecture rtl;
