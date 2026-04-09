# ===========================================================
# FILE:         tests/test_datasheet_gen.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
"""Tests for agents/datasheet_gen.py."""
import os
import pytest
from ir import IR, Port
from agents.datasheet_gen import generate_datasheet


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _minimal_ir(design_name: str = "test_ip") -> IR:
    """Return a minimal IR with two ports and no register map."""
    return IR(
        design_name=design_name,
        hdl_source="",
        hdl_language="vhdl",
        ports=[
            Port(name="clk",    direction="input",  width=1, role="clock"),
            Port(name="rst_n",  direction="input",  width=1, role="reset_n"),
            Port(name="irq",    direction="output", width=1, role="data"),
        ],
        parameters={},
        emission_target="vivado",
        output_dir="./out",
    )


def _axi_ir() -> IR:
    """Return an IR that has AXI-Lite slave ports."""
    return IR(
        design_name="axi_ip",
        hdl_source="",
        hdl_language="vhdl",
        ports=[
            Port(name="axi_aclk",      direction="input",  width=1, role="clock"),
            Port(name="s_axi_awvalid", direction="input",  width=1, role="control"),
            Port(name="s_axi_awready", direction="output", width=1, role="data"),
            Port(name="irq",           direction="output", width=1, role="data"),
        ],
        parameters={"G_CLK_FREQ_HZ": "100_000_000"},
        emission_target="vivado",
        output_dir="./out",
    )


class _FakeReqResult:
    """Minimal stand-in for ReqParseResult."""
    def __init__(self, count: int = 5):
        self.requirements = {f"REQ-{i:03d}": {} for i in range(count)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_datasheet_gen_creates_file(tmp_path):
    ir = _minimal_ir()
    out = str(tmp_path / "DATASHEET.md")
    result = generate_datasheet(ir, out_path=out)
    assert result == out
    assert os.path.isfile(out)


def test_datasheet_gen_contains_required_sections(tmp_path):
    ir = _minimal_ir()
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out)
    content = open(out, encoding="utf-8").read()
    for heading in [
        "## Identity",
        "## Maturity",
        "## Quick Start",
        "## Known Limitations",
        "## Resource Utilization",
        "## Power Estimate",
        "## Tested With",
        "## Revision History",
    ]:
        assert heading in content, f"Missing section: {heading}"


def test_datasheet_gen_design_name_in_output(tmp_path):
    ir = _minimal_ir("my_widget")
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out)
    content = open(out, encoding="utf-8").read()
    assert "my_widget" in content


def test_datasheet_gen_ports_in_instantiation(tmp_path):
    ir = _minimal_ir()
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out)
    content = open(out, encoding="utf-8").read()
    # The "irq" port should appear in the port map
    assert "irq" in content


def test_datasheet_gen_axi_protocol_detected(tmp_path):
    ir = _axi_ir()
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out)
    content = open(out, encoding="utf-8").read()
    assert "AXI4-Lite" in content


def test_datasheet_gen_preserves_limitations(tmp_path):
    # Write an existing DATASHEET.md with a custom limitation bullet
    existing = str(tmp_path / "existing_DATASHEET.md")
    _write_existing_datasheet(existing, limitations=[
        "- Custom limitation note.",
        "",
        "*This section grows as integration experience accumulates.*",
    ])
    ir = _minimal_ir()
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out, existing_path=existing)
    content = open(out, encoding="utf-8").read()
    assert "- Custom limitation note." in content


def test_datasheet_gen_preserves_utilization_rows(tmp_path):
    util_row = "| Artix-7 | Vivado | 312 | 580 | 2 BRAM36 | 0 | 125.4 | timing OK | 2026-04-08 |"
    existing = str(tmp_path / "existing_DATASHEET.md")
    _write_existing_datasheet(existing, util_rows=[util_row])
    ir = _minimal_ir()
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out, existing_path=existing)
    content = open(out, encoding="utf-8").read()
    assert "Artix-7" in content
    assert "312" in content


def test_datasheet_gen_revision_appended_on_change(tmp_path):
    # First generation (no existing file) — uses default 1 revision row
    ir = _minimal_ir()
    first = str(tmp_path / "first.md")
    generate_datasheet(ir, out_path=first)

    # Second generation with existing file but different req count triggers a change
    req_result = _FakeReqResult(count=99)
    second = str(tmp_path / "second.md")
    generate_datasheet(
        ir,
        req_result=req_result,
        out_path=second,
        existing_path=first,
    )
    first_content = open(first, encoding="utf-8").read()
    second_content = open(second, encoding="utf-8").read()

    def _count_rev_rows(text: str) -> int:
        in_section = False
        header_seen = False
        count = 0
        for line in text.splitlines():
            if line.strip() == "## Revision History":
                in_section = True
                continue
            if not in_section:
                continue
            if line.strip() == "---":
                break
            if "|--" in line:
                header_seen = True
                continue
            if header_seen and line.strip().startswith("|"):
                count += 1
        return count

    assert _count_rev_rows(second_content) > _count_rev_rows(first_content)


def test_datasheet_gen_no_revision_appended_if_unchanged(tmp_path):
    ir = _minimal_ir()
    first = str(tmp_path / "first.md")
    generate_datasheet(ir, out_path=first)

    second = str(tmp_path / "second.md")
    generate_datasheet(ir, out_path=second, existing_path=first)

    def _count_rev_rows(text: str) -> int:
        in_section = False
        header_seen = False
        count = 0
        for line in text.splitlines():
            if line.strip() == "## Revision History":
                in_section = True
                continue
            if not in_section:
                continue
            if line.strip() == "---":
                break
            if "|--" in line:
                header_seen = True
                continue
            if header_seen and line.strip().startswith("|"):
                count += 1
        return count

    assert _count_rev_rows(second_content := open(second).read()) == \
           _count_rev_rows(open(first).read())


def test_datasheet_gen_trailing_newline(tmp_path):
    ir = _minimal_ir()
    out = str(tmp_path / "DATASHEET.md")
    generate_datasheet(ir, out_path=out)
    content = open(out, encoding="utf-8").read()
    assert content.endswith("\n")


# ---------------------------------------------------------------------------
# Helper: write a minimal existing DATASHEET.md for preservation tests
# ---------------------------------------------------------------------------

def _write_existing_datasheet(
    path: str,
    limitations: list[str] | None = None,
    util_rows: list[str] | None = None,
) -> None:
    """Write a minimal DATASHEET.md with given preserved content."""
    if limitations is None:
        limitations = [
            "- No known limitations at this stage.",
            "",
            "*This section grows as integration experience accumulates.*",
        ]
    lim_block = "\n".join(limitations)

    util_block = ""
    if util_rows:
        util_block = "\n".join(util_rows)

    content = f"""# IP Data Sheet: test_ip

## Identity

| Field        | Value                                            |
|--------------|--------------------------------------------------|
| Design Name  | test_ip                                          |

---

## Maturity

| Milestone                        | Status     | Date       |
|----------------------------------|------------|------------|
| Requirements specification       | Pending    | —          |

---

## Quick Start

```vhdl
u_test_ip : entity work.test_ip port map ();
```

---

## Known Limitations and Integration Notes

{lim_block}

---

## Resource Utilization

Add a row each time synthesis is run on a new target.
Fmax is post-route worst-case at the stated speed grade.
RAM Blocks cell specifies vendor type (e.g. "2 BRAM36",
"1 M10K", "3 EBR"). LUTs/ALMs uses vendor-appropriate term.

| Target Device | Tool | LUTs/ALMs | FFs | RAM Blocks | DSP | Fmax (MHz) | Notes | Date |
|---------------|------|-----------|-----|------------|-----|------------|-------|------|
{util_block}

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

---

## Revision History

| Rev | Date       | Author    | Description                  |
|-----|------------|-----------|------------------------------|
| 0.1 | 2026-04-07 | S. Belton | Initial — stub phase         |
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
