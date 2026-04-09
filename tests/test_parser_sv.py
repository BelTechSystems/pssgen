# ===========================================================
# FILE:         tests/test_parser_sv.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
"""Tests for parser/systemverilog.py."""
import os
import pytest

from parser.systemverilog import parse
from parser.dispatch import parse_source

COUNTER_SV = os.path.join(os.path.dirname(__file__), "fixtures", "counter.sv")
BALU_SV = os.path.join(
    os.path.dirname(__file__),
    "..", "ip", "buffered_axi_lite_uart", "sv", "buffered_axi_lite_uart.sv",
)


@pytest.fixture(scope="module")
def counter_ir():
    return parse(COUNTER_SV, None)


@pytest.fixture(scope="module")
def balu_ir():
    return parse(BALU_SV, None)


# ---------------------------------------------------------------------------
# counter.sv tests
# ---------------------------------------------------------------------------

def test_parse_sv_counter_port_count(counter_ir):
    assert len(counter_ir.ports) == 5


def test_parse_sv_counter_design_name(counter_ir):
    assert counter_ir.design_name == "up_down_counter"


def test_parse_sv_counter_language(counter_ir):
    assert counter_ir.hdl_language == "systemverilog"


def test_parse_sv_counter_parameter(counter_ir):
    assert "WIDTH" in counter_ir.parameters
    assert counter_ir.parameters["WIDTH"] == "8"


def test_parse_sv_counter_roles(counter_ir):
    roles = {p.name: p.role for p in counter_ir.ports}
    assert roles["clk"] == "clock"
    assert roles["rst_n"] == "reset_n"
    assert roles["enable"] == "control"
    assert roles["up_down"] == "control"
    assert roles["count"] == "data"


def test_parse_sv_counter_widths(counter_ir):
    widths = {p.name: p.width for p in counter_ir.ports}
    assert widths["clk"] == 1
    assert widths["count"] == 8


# ---------------------------------------------------------------------------
# buffered_axi_lite_uart.sv tests
# ---------------------------------------------------------------------------

def test_parse_sv_balu_port_count(balu_ir):
    assert len(balu_ir.ports) == 24


def test_parse_sv_balu_design_name(balu_ir):
    assert balu_ir.design_name == "buffered_axi_lite_uart"


def test_parse_sv_balu_language(balu_ir):
    assert balu_ir.hdl_language == "systemverilog"


def test_parse_sv_balu_parameters(balu_ir):
    params = balu_ir.parameters
    assert "P_CLK_FREQ_HZ" in params
    assert "P_DEFAULT_BAUD" in params
    assert "P_FIFO_DEPTH" in params
    assert "P_TIMEOUT_DEFAULT" in params
    assert params["P_CLK_FREQ_HZ"] == "100000000"
    assert params["P_DEFAULT_BAUD"] == "115200"
    assert params["P_FIFO_DEPTH"] == "16"
    assert params["P_TIMEOUT_DEFAULT"] == "255"


def test_parse_sv_balu_axi_ports_present(balu_ir):
    names = {p.name for p in balu_ir.ports}
    assert "s_axi_awvalid" in names
    assert "s_axi_rresp" in names


def test_parse_sv_balu_uart_ports_present(balu_ir):
    names = {p.name for p in balu_ir.ports}
    assert "uart_tx" in names
    assert "uart_rx" in names
    assert "irq" in names


# ---------------------------------------------------------------------------
# Dispatch test
# ---------------------------------------------------------------------------

def test_parse_sv_dispatch():
    ir = parse_source(COUNTER_SV, None)
    assert ir.design_name == "up_down_counter"
    assert ir.hdl_language == "systemverilog"
