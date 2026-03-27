# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""Unit tests for the constrained VHDL parser."""

from __future__ import annotations

import pytest

from parser.vhdl import ParseError, parse


FIXTURE = "tests/fixtures/counter.vhd"


def test_parse_vhdl_counter_port_count() -> None:
    """Verify that five top-level ports are extracted from the canonical fixture."""
    ir = parse(FIXTURE, top_module=None)
    assert len(ir.ports) == 5


def test_parse_vhdl_counter_design_name() -> None:
    """Verify that design_name is parsed as up_down_counter."""
    ir = parse(FIXTURE, top_module=None)
    assert ir.design_name == "up_down_counter"


def test_parse_vhdl_counter_roles() -> None:
    """Verify VHDL role classification matches v0 role heuristics."""
    ir = parse(FIXTURE, top_module=None)
    roles = {p.name: p.role for p in ir.ports}
    assert roles["clk"] == "clock"
    assert roles["rst_n"] == "reset_n"
    assert roles["enable"] == "control"
    assert roles["up_down"] == "control"
    assert roles["count"] == "data"


def test_parse_vhdl_counter_widths() -> None:
    """Verify scalar and vector widths for canonical VHDL fixture ports."""
    ir = parse(FIXTURE, top_module=None)
    widths = {p.name: p.width for p in ir.ports}
    assert widths["clk"] == 1
    assert widths["count"] == 8


def test_parse_vhdl_counter_language() -> None:
    """Verify parsed IR language is tagged as vhdl."""
    ir = parse(FIXTURE, top_module=None)
    assert ir.hdl_language == "vhdl"


def test_parse_vhdl_counter_generics() -> None:
    """Verify integer generic defaults are extracted into parameters."""
    ir = parse(FIXTURE, top_module=None)
    assert "WIDTH" in ir.parameters
    assert ir.parameters["WIDTH"] == "8"


def test_parse_vhdl_unsupported_type(tmp_path) -> None:
    """Verify unsupported port types raise ParseError with port/type detail."""
    source = tmp_path / "bad_port_type.vhd"
    source.write_text(
        """library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity bad_design is
    port (
        bad_port : in integer
    );
end entity bad_design;

architecture rtl of bad_design is
begin
end architecture rtl;
""",
        encoding="utf-8",
    )

    with pytest.raises(ParseError, match=r"Unsupported VHDL port type 'integer'.*bad_port"):
        parse(str(source), top_module=None)
