# IP Data Sheet: Buffered AXI-Lite UART

## Identity

| Field        | Value                                            |
|--------------|--------------------------------------------------|
| Design Name  | buffered_axi_lite_uart                           |
| Spec         | BALU-RS-001 Rev 0.4                              |
| Version      | 0.1.0                                            |
| Status       | IN DEVELOPMENT — architecture stub               |
| Author       | S. Belton, BelTech Systems LLC                   |
| License      | MIT                                              |
| Bus Protocol | AXI4-Lite (ARM IHI0022E), 32-bit data, 8-bit addr|

---

## Maturity

| Milestone                        | Status     | Date       |
|----------------------------------|------------|------------|
| Requirements specification       | ✓ Complete | 2026-04-07 |
| VCRM — 141 requirements          | ✓ Complete | 2026-04-07 |
| Register map spreadsheet         | ✓ Complete | 2026-04-07 |
| VHDL entity + architecture stub  | ✓ Complete | 2026-04-07 |
| SystemVerilog module + stub      | Pending    | —          |
| Architecture implementation      | Pending    | —          |
| pssgen gap report — all closed   | Pending    | —          |
| Simulation — block level         | Pending    | —          |
| Synthesis — Vivado WebPACK       | Pending    | —          |
| Synthesis — Yosys + nextpnr      | Pending    | —          |
| Board bring-up — ZUBoard 1CG     | Pending    | —          |
| Board bring-up — Basys 3         | Pending    | —          |

---

## Quick Start

VHDL instantiation at default generics:
```vhdl
u_uart : entity work.buffered_axi_lite_uart
  generic map (
    G_CLK_FREQ_HZ     => 100_000_000,
    G_DEFAULT_BAUD    => 115_200,
    G_FIFO_DEPTH      => 16,
    G_TIMEOUT_DEFAULT => 255
  )
  port map (
    axi_aclk      => clk_s,
    axi_aresetn   => resetn_s,
    s_axi_awvalid => m_axi_awvalid_s,
    s_axi_awready => m_axi_awready_s,
    s_axi_awaddr  => m_axi_awaddr_s,
    s_axi_awprot  => m_axi_awprot_s,
    s_axi_wvalid  => m_axi_wvalid_s,
    s_axi_wready  => m_axi_wready_s,
    s_axi_wdata   => m_axi_wdata_s,
    s_axi_wstrb   => m_axi_wstrb_s,
    s_axi_bvalid  => m_axi_bvalid_s,
    s_axi_bready  => m_axi_bready_s,
    s_axi_bresp   => m_axi_bresp_s,
    s_axi_arvalid => m_axi_arvalid_s,
    s_axi_arready => m_axi_arready_s,
    s_axi_araddr  => m_axi_araddr_s,
    s_axi_arprot  => m_axi_arprot_s,
    s_axi_rvalid  => m_axi_rvalid_s,
    s_axi_rready  => m_axi_rready_s,
    s_axi_rdata   => m_axi_rdata_s,
    s_axi_rresp   => m_axi_rresp_s,
    uart_tx       => uart_tx_s,
    uart_rx       => uart_rx_s,
    irq           => uart_irq_s
  );
```

See BALU-RS-001 Section 3 for generic ranges and constraints.
See the register map spreadsheet for the complete field list.

---

## Known Limitations and Integration Notes

- BAUD_TUNING writes are silently ignored while UART_EN=1.
  Disable the UART before changing baud rate at runtime.
- G_FIFO_DEPTH must be a power of 2 in range 8–256.
  Elaboration fails with a descriptive message otherwise.
- The RX input is synchronised with a two-stage FF chain.
  Minimum recognisable pulse width on uart_rx is two
  axi_aclk cycles.
- STATUS is a combinatorial register. Hold the sampled
  value in software if multi-cycle consistency is needed.
- INT_CLEAR is write-only. Reads always return 0x00000000.
- TX_DATA writes while TX_FULL is asserted are silently
  discarded. Poll STATUS[TX_FULL] or use the TX_THRESH
  interrupt before writing.

*This section grows as integration experience accumulates.*

---

## Resource Utilization

Add a row each time synthesis is run on a new target.
Fmax is post-route worst-case at the stated speed grade.
RAM Blocks cell specifies vendor type (e.g. "2 BRAM36",
"1 M10K", "3 EBR"). LUTs/ALMs uses vendor-appropriate term.

| Target Device | Tool | LUTs/ALMs | FFs | RAM Blocks | DSP | Fmax (MHz) | Notes | Date |
|---------------|------|-----------|-----|------------|-----|------------|-------|------|

---

## Power Estimate

Add a row each time a power analysis is run.
Dynamic and static power at typical conditions unless noted.

| Target Device | Tool | Dynamic (mW) | Static (mW) | Notes | Date |
|---------------|------|-------------|-------------|-------|------|

---

## Tested With

| Item    | Version | Notes                             |
|---------|---------|-----------------------------------|
| pssgen  | v5a     | Verification artifact generation  |
| Vivado  | —       | Pending first synthesis run       |
| GHDL    | —       | Pending simulation                |
| Questa  | —       | UVM simulation target             |
| Yosys   | —       | Pending synthesis run             |

---

## Revision History

| Rev | Date       | Author    | Description                  |
|-----|------------|-----------|------------------------------|
| 0.1 | 2026-04-07 | S. Belton | Initial — stub phase         |
