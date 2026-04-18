# Phase 2 VSL Grammar Gaps

## GAP-001: AXI_WRITE_ORDER action

**Affected goal:** COV-012 (AXI_WRITE_ORDER) — buffered_axi_lite_uart

**Description:** AXI-Lite write channel ordering (AWVALID-first vs
WVALID-first) is a protocol-level stimulus that cannot be expressed
with the current WRITE/READ/WAIT/POLL action set. The action requires
direct control of AXI handshake signal sequencing below the
register-model abstraction layer.

**Required VSL extension:** New action `AXI_WRITE_ORDER` with params:
  order=AW_FIRST|W_FIRST, addr=<hex>, data=<hex>

**Blocking:** Phase 1 BALU simulation (COV-012 will use SEQ_PENDING stub)

**Target:** Block 2 or D-035 VSL grammar extension
