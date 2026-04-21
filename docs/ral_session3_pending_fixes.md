# RAL Session 3 Pending Fixes

## Root causes identified during smoke→regression transition

### Issue 1: BAUD_TUNING corruption between sequences
- COV-001 writes 0x10D6, no reset between sequences
- All subsequent loopback polls time out
- Fix: Add ARESETn_seq to interface, dut_rst_n = rst_n & ARESETn_seq
  in tb_top, add reset_dut() to base_seq, call at top of every body()

### Issue 2: COV-007 wrong stimulus
- RTL only fires ev_tx_empty_s after a byte finishes transmitting
- No byte written = no interrupt ever
- Fix: Add TX_DATA write before polling, increase timeout 100→3000

### Issue 3: COV-015 wrong STATUS reset value
- Expected 0x01 but RTL reset value is 0x140 (TX_EMPTY+RX_EMPTY)
- Fix: Update expected value in seq_RCOV015

## Status
- Smoke test: PASSED (0 errors, 0 fatals)
- Full regression: NOT RUN — fixes required first
- Next session: implement fixes in short focused prompts

## Regression Run 1 Results — fdb25ee base

### Passing sequences
COV-001, COV-005, COV-006, COV-011, COV-014, COV-015, COV-017 (partial)

### Fix 4: Loopback sequences need BAUD_TUNING re-init after reset
Affected: COV-002, COV-003, COV-004, COV-008, COV-009, COV-017
Root cause: reset_dut() clears BAUD_TUNING to 0x0, NCO stops,
TX bytes transmit but RX never receives
Fix: Add reg_write(reg_model.BAUD, 32'h000010D6) after reset_dut()
in each affected sequence body()

### Fix 5: COV-007 wrong interrupt bit mask
Current mask polls for TX_THRESH (bit6=0x40)
Need TX_EMPTY (bit4=0x10)
Fix: Change poll mask from 0x40 to 0x10 in seq_RCOV007

### Fix 6: Scoreboard SLVERR severity
Expected SLVERR responses logged as UVM_ERROR
Should be UVM_INFO
Fix: buffered_axi_lite_uart_scoreboard.sv — change severity
for known SLVERR addresses

### Fix 7: tb_top AWPROT not connected
Harmless warning but clean it up
Fix: Tie s_axi_awprot = 3'b000 in tb_top

## Target: 0 UVM_ERROR, 0 UVM_FATAL, 0 UVM_WARNING (except SB disabled)

### Fix 12 REVISED — correct BAUD_TUNING value
Root cause confirmed: BAUD_TUNING must have bits[31:28]=0000
for correct 16x oversampling relationship.
Fix 8 (0x10000000) and Fix 11 (0x10100000) both have
bits[31:28]=0001 — RX engine broken by NCO design constraint.

Correct value: 0x00800000
  - bits[31:28] = 0000 ✓
  - baud pulse every 512 cycles
  - byte frame = 5,120 cycles
  - poll window = 15,000 cycles (2.9x margin) ✓
