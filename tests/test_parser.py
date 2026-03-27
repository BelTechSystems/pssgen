"""Unit tests for the Verilog parser."""
import pytest
from parser.verilog import parse, ParseError


FIXTURE = "tests/fixtures/counter.v"


def test_parse_verilog_counter_port_count():
    ir = parse(FIXTURE, "up_down_counter")
    assert len(ir.ports) == 5


def test_parse_verilog_counter_design_name():
    ir = parse(FIXTURE, None)
    assert ir.design_name == "up_down_counter"


def test_parse_verilog_counter_roles():
    ir = parse(FIXTURE, None)
    roles = {p.name: p.role for p in ir.ports}
    assert roles["clk"]     == "clock"
    assert roles["rst_n"]   == "reset_n"
    assert roles["enable"]  == "control"
    assert roles["up_down"] == "control"
    assert roles["count"]   == "data"


def test_parse_verilog_counter_widths():
    ir = parse(FIXTURE, None)
    widths = {p.name: p.width for p in ir.ports}
    assert widths["clk"]    == 1
    assert widths["count"]  == 8


def test_parse_verilog_counter_language():
    ir = parse(FIXTURE, None)
    assert ir.hdl_language == "verilog"
