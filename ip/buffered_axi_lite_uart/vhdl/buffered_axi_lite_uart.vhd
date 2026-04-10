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
--   STATUS_MUX     : STATUS_p — combinatorial STATUS register
--
-- Dependencies:
--   ieee.std_logic_1164
--   ieee.numeric_std
--   ieee.math_real (elaboration only — for baud reset calc)
--
-- History:
--   2026-04-07  S. Belton  Initial entity + architecture stub
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
  signal arready_s : std_logic;
  -- Read address ready — registered
  signal rvalid_s  : std_logic;
  -- Read data valid — registered
  signal rdata_s   : std_logic_vector(31 downto 0);
  -- Read data — registered
  signal rresp_s   : std_logic_vector(1 downto 0);
  -- Read response code — registered

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

  -- ---- NCO baud generator ----------------------------------
  signal nco_accum_s : unsigned(31 downto 0);
  -- NCO phase accumulator — wraps on overflow
  signal baud_pulse_s : std_logic;
  -- Single-cycle pulse at the baud rate (carry-out)
  signal baud_pulse_16x_s : std_logic;
  -- Single-cycle pulse at 16x baud rate for RX mid-bit sampling

  -- ---- TX FIFO ---------------------------------------------
  signal tx_fifo_mem_s : fifo_mem_t;
  -- TX FIFO storage
  signal tx_wr_ptr_s   : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- TX write pointer (extra MSB for full/empty detection)
  signal tx_rd_ptr_s   : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- TX read pointer
  signal tx_full_s     : std_logic;
  -- TX FIFO full flag (combinatorial)
  signal tx_empty_s    : std_logic;
  -- TX FIFO empty flag (combinatorial)
  signal tx_level_s    : unsigned(7 downto 0);
  -- TX FIFO occupancy count (combinatorial)

  -- ---- RX FIFO ---------------------------------------------
  signal rx_fifo_mem_s : fifo_mem_t;
  -- RX FIFO storage
  signal rx_wr_ptr_s   : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- RX write pointer
  signal rx_rd_ptr_s   : unsigned(FIFO_ADDR_WIDTH_c downto 0);
  -- RX read pointer
  signal rx_full_s     : std_logic;
  -- RX FIFO full flag (combinatorial)
  signal rx_empty_s    : std_logic;
  -- RX FIFO empty flag (combinatorial)
  signal rx_level_s    : unsigned(7 downto 0);
  -- RX FIFO occupancy count (combinatorial)

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

  -- ---- Timeout controller ----------------------------------
  signal timeout_cnt_s  : unsigned(15 downto 0);
  -- Receive timeout counter (counts baud pulses)
  signal timeout_flag_s : std_logic;
  -- TIMEOUT_FLAG — set on expiry, cleared when RX FIFO empty

  -- ---- Interrupt event pulses (single-cycle sources) -------
  signal ev_tx_thresh_s : std_logic;
  signal ev_rx_thresh_s : std_logic;
  signal ev_tx_empty_s  : std_logic;
  signal ev_rx_full_s   : std_logic;
  signal ev_parity_err_s : std_logic;
  signal ev_frame_err_s  : std_logic;
  signal ev_overrun_s   : std_logic;
  signal ev_timeout_s   : std_logic;
  -- Single-cycle event pulses feeding INT_STATUS sticky flags

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

  -- NCO baud pulse — stub: MSB of accumulator (will be carry-out when implemented)
  baud_pulse_s <= nco_accum_s(31);
  baud_pulse_16x_s <= nco_accum_s(27);
  -- STUB: bit 27 produces 16x baud pulse from same NCO.
  -- Replace with carry from dedicated counter in NCO_ACCUM_p.

  -- Event pulse stubs — all inactive until owning
  -- processes are implemented. Remove these assignments
  -- and drive from the owning process at implementation.
  ev_tx_thresh_s  <= '0';  -- TX_ENGINE_p
  ev_rx_thresh_s  <= '0';  -- RX_ENGINE_p
  ev_tx_empty_s   <= '0';  -- TX_FIFO_p
  ev_rx_full_s    <= '0';  -- RX_FIFO_p
  ev_parity_err_s <= '0';  -- RX_ENGINE_p
  ev_frame_err_s  <= '0';  -- RX_ENGINE_p
  ev_overrun_s    <= '0';  -- RX_FIFO_p
  ev_timeout_s    <= '0';  -- TIMEOUT_p

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
  -- Process stubs — all synchronous to axi_aclk,
  -- synchronous active-low reset (axi_aresetn).
  -- No asynchronous resets.
  -- ===========================================================

  -- -------------------------------------------------------------
  -- Process : NCO_ACCUM_p
  -- Block   : NCO_BAUD
  -- Purpose : NCO phase accumulator; produces baud_pulse_s on carry
  -- Note    : Implementation must also produce a 16x oversample
  --           pulse (baud_pulse_16x_s) using NCO MSB-4 for
  --           mid-bit RX sampling. See UART-BR requirement group.
  -- -------------------------------------------------------------
  NCO_ACCUM_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: nco_accum_s <= BAUD_TUNING_RESET_c
        null;
      else
        -- Add baud_tuning_s each cycle; carry out is baud_pulse_s
        null;
      end if;
    end if;
  end process NCO_ACCUM_p;

  -- -------------------------------------------------------------
  -- Process : AXI_AW_LATCH_p
  -- Block   : AXI_WRITE_CTRL
  -- Purpose : Latch AXI-Lite write address when awvalid & awready
  -- -------------------------------------------------------------
  AXI_AW_LATCH_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: aw_valid_lat_s <= '0'; aw_addr_lat_s <= (others => '0')
        null;
      else
        -- Capture s_axi_awaddr into aw_addr_lat_s when handshake completes
        null;
      end if;
    end if;
  end process AXI_AW_LATCH_p;

  -- -------------------------------------------------------------
  -- Process : AXI_W_LATCH_p
  -- Block   : AXI_WRITE_CTRL
  -- Purpose : Latch AXI-Lite write data when wvalid & wready
  -- -------------------------------------------------------------
  AXI_W_LATCH_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: w_valid_lat_s <= '0'; w_data_lat_s <= (others => '0')
        null;
      else
        -- Capture s_axi_wdata/wstrb into latches when handshake completes
        null;
      end if;
    end if;
  end process AXI_W_LATCH_p;

  -- -------------------------------------------------------------
  -- Process : AXI_WRITE_RESP_p
  -- Block   : AXI_WRITE_CTRL
  -- Purpose : Decode write address, dispatch to register file,
  --           drive bvalid/bresp (OKAY or SLVERR for undefined addr)
  -- -------------------------------------------------------------
  AXI_WRITE_RESP_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: bvalid_s <= '0'; bresp_s <= AXI_OKAY_c
        null;
      else
        -- When both latches valid, dispatch write; assert bvalid_s
        null;
      end if;
    end if;
  end process AXI_WRITE_RESP_p;

  -- -------------------------------------------------------------
  -- Process : AXI_READ_p
  -- Block   : AXI_READ_CTRL
  -- Purpose : Decode read address, mux register data to rdata_s,
  --           drive arready/rvalid/rresp
  -- -------------------------------------------------------------
  AXI_READ_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: arready_s <= '1'; rvalid_s <= '0'; rdata_s <= (others => '0')
        null;
      else
        -- Accept read address; mux register file output to rdata_s
        null;
      end if;
    end if;
  end process AXI_READ_p;

  -- -------------------------------------------------------------
  -- Process : REG_WRITE_p
  -- Block   : REG_BLOCK
  -- Purpose : Apply reset values to all writable registers on reset;
  --           decode AXI write address and update register file otherwise.
  --           BAUD_TUNING write blocked while ctrl_s(7)=UART_EN.
  --           Single process owns all register signals to avoid
  --           multiple-driver conflicts.
  -- -------------------------------------------------------------
  REG_WRITE_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- ctrl_s <= x"00"; baud_tuning_s <= BAUD_TUNING_RESET_c;
        -- fifo_ctrl_s <= FIFO_THRESH_RESET_c & FIFO_THRESH_RESET_c;
        -- timeout_val_s <= std_logic_vector(to_unsigned(G_TIMEOUT_DEFAULT,16));
        -- int_enable_s <= x"00"; int_status_s <= x"00"; scratch_s <= (others => '0')
        null;
      else
        -- Case aw_addr_lat_s: update register; INT_CLEAR uses W1C logic
        null;
      end if;
    end if;
  end process REG_WRITE_p;

  -- -------------------------------------------------------------
  -- Process : TX_FIFO_p
  -- Block   : TX_FIFO
  -- Purpose : Push TX_DATA writes into tx_fifo_mem_s; pop on
  --           TX engine request when not tx_empty_s
  -- -------------------------------------------------------------
  TX_FIFO_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: tx_wr_ptr_s <= (others => '0'); tx_rd_ptr_s <= (others => '0')
        null;
      else
        -- Push: increment tx_wr_ptr_s; Pop: increment tx_rd_ptr_s
        null;
      end if;
    end if;
  end process TX_FIFO_p;

  -- -------------------------------------------------------------
  -- Process : RX_FIFO_p
  -- Block   : RX_FIFO
  -- Purpose : Push received bytes from RX engine; pop on RX_DATA read;
  --           set ev_overrun_s if push attempted while rx_full_s
  -- -------------------------------------------------------------
  RX_FIFO_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: rx_wr_ptr_s <= (others => '0'); rx_rd_ptr_s <= (others => '0')
        null;
      else
        -- Push on RX engine valid; Pop on RX_DATA AXI read
        null;
      end if;
    end if;
  end process RX_FIFO_p;

  -- -------------------------------------------------------------
  -- Process : TX_ENGINE_p
  -- Block   : TX_ENGINE
  -- Purpose : Load tx_shift_s from TX FIFO, clock out start/data/stop
  --           at baud_pulse_s rate; drives uart_tx via concurrent assign
  -- -------------------------------------------------------------
  TX_ENGINE_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: tx_shift_s <= (others => '1'); tx_bit_cnt_s <= (others => '0')
        --        tx_busy_s <= '0'
        null;
      else
        -- On baud_pulse_s: shift right; set tx_busy_s; assert ev_tx_thresh_s
        null;
      end if;
    end if;
  end process TX_ENGINE_p;

  -- -------------------------------------------------------------
  -- Process : RX_ENGINE_p
  -- Block   : RX_ENGINE
  -- Purpose : Two-stage synchronise uart_rx; detect start bit;
  --           sample data at mid-baud using baud_pulse_16x_s;
  --           push to RX FIFO on stop bit. Uses 16x oversampling
  --           for noise immunity and phase alignment.
  -- -------------------------------------------------------------
  RX_ENGINE_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: rx_sync_s <= "11"; rx_busy_s <= '0'; rx_bit_cnt_s <= (others => '0')
        null;
      else
        -- Synchronise uart_rx; detect falling edge for start; sample at half-baud
        null;
      end if;
    end if;
  end process RX_ENGINE_p;

  -- -------------------------------------------------------------
  -- Process : INT_CTRL_p
  -- Block   : INT_CTRL
  -- Purpose : Latch event pulses into int_status_s sticky flags;
  --           clear on INT_CLEAR write (W1C); irq driven by concurrent assign
  -- -------------------------------------------------------------
  INT_CTRL_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: int_status_s <= x"00"
        null;
      else
        -- OR event pulses into sticky flags; mask with W1C clear from REG_WRITE_p
        null;
      end if;
    end if;
  end process INT_CTRL_p;

  -- -------------------------------------------------------------
  -- Process : TIMEOUT_p
  -- Block   : TIMEOUT_CTRL
  -- Purpose : Count baud pulses since last RX byte; assert ev_timeout_s
  --           when timeout_cnt_s reaches timeout_val_s; clear on RX FIFO pop
  -- -------------------------------------------------------------
  TIMEOUT_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        -- Reset: timeout_cnt_s <= (others => '0'); timeout_flag_s <= '0'
        null;
      else
        -- Increment on baud_pulse_s; reset on RX FIFO pop; set flag on expiry
        null;
      end if;
    end if;
  end process TIMEOUT_p;

  -- -------------------------------------------------------------
  -- Process : STATUS_p
  -- Block   : STATUS_MUX
  -- Purpose : Combinatorial assembly of the STATUS register from
  --           FIFO flags, engine busy signals, and UART error flags.
  -- Note    : STUB ONLY — replace with process(all) at implementation.
  --           An empty process(all) is not valid VHDL; clocked here.
  --           No registered state. STATUS reflects current-cycle
  --           hardware values with zero additional latency when
  --           implemented correctly as combinatorial.
  -- -------------------------------------------------------------
  STATUS_p : process(axi_aclk)
  begin
    if rising_edge(axi_aclk) then
      if axi_aresetn = '0' then
        null;
      else
        -- Assemble STATUS[31:0] from tx_full_s, tx_empty_s, rx_full_s,
        -- rx_empty_s, tx_busy_s, rx_busy_s, parity/frame error flags
        null;
      end if;
    end if;
  end process STATUS_p;

end architecture rtl;
