# IP Data Sheet: buffered_axi_lite_uart

## Identity

| Field        | Value                                            |
|--------------|--------------------------------------------------|
| Design Name  | buffered_axi_lite_uart                           |
| Spec         | —                                                |
| Version      | 0.1.0                                            |
| Status       | IN DEVELOPMENT — architecture stub               |
| Author       | S. Belton, BelTech Systems LLC                   |
| License      | MIT                                              |
| Bus Protocol | AXI4-Lite (ARM IHI0022E), 32-bit data, 8-bit addr |

---

## Maturity

| Milestone                        | Status     | Date       |
|----------------------------------|------------|------------|
| Requirements specification       | ✓ Complete | 2026-04-11 |
| VCRM — 141 requirements          | ✓ Complete | 2026-04-11 |
| Register map spreadsheet         | Pending    | —          |
| VHDL entity + architecture stub  | ✓ Complete | 2026-04-11 |
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
u_buffered_axi_lite_uart : entity work.buffered_axi_lite_uart
  generic map (
    G_CLK_FREQ_HZ          => 100_000_000,
    G_DEFAULT_BAUD         => 115_200,
    G_FIFO_DEPTH           => 16,
    G_TIMEOUT_DEFAULT      => 255
  )
  port map (
    axi_aclk           => clk_s,
    axi_aresetn        => resetn_s,
    s_axi_awvalid      => s_axi_awvalid_s,
    s_axi_awready      => s_axi_awready_s,
    s_axi_awaddr       => s_axi_awaddr_s,
    s_axi_awprot       => s_axi_awprot_s,
    s_axi_wvalid       => s_axi_wvalid_s,
    s_axi_wready       => s_axi_wready_s,
    s_axi_wdata        => s_axi_wdata_s,
    s_axi_wstrb        => s_axi_wstrb_s,
    s_axi_bvalid       => s_axi_bvalid_s,
    s_axi_bready       => s_axi_bready_s,
    s_axi_bresp        => s_axi_bresp_s,
    s_axi_arvalid      => s_axi_arvalid_s,
    s_axi_arready      => s_axi_arready_s,
    s_axi_araddr       => s_axi_araddr_s,
    s_axi_arprot       => s_axi_arprot_s,
    s_axi_rvalid       => s_axi_rvalid_s,
    s_axi_rready       => s_axi_rready_s,
    s_axi_rdata        => s_axi_rdata_s,
    s_axi_rresp        => s_axi_rresp_s,
    uart_tx            => uart_tx_s,
    uart_rx            => uart_rx_s,
    irq                => irq_s
  );
```

See BALU-RS-001 Section 3 for generic ranges and constraints.
See the register map spreadsheet for the complete field list.

---

## Known Limitations and Integration Notes

- No known limitations at this stage.

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
