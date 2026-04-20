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
