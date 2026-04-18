# ===========================================================
# FILE:         tests/test_vsl_parser.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for parse_vsl_stimulus() in agents/scaffold_gen.py.
#   Covers empty/NONE inputs, single/multi-step sequences, param types,
#   malformed input rejection, and a realistic AXI-Lite UART scenario.
#
# LAYER:        4 — checkers / tests
# PHASE:        D-034
#
# HISTORY:
#   D-034  2026-04-18  SB  Initial implementation
#
# ===========================================================
import pytest
from agents.scaffold_gen import parse_vsl_stimulus


def test_empty_string_returns_empty_list():
    assert parse_vsl_stimulus("") == []


def test_none_string_returns_empty_list():
    assert parse_vsl_stimulus("NONE") == []


def test_none_value_returns_empty_list():
    assert parse_vsl_stimulus(None) == []


def test_single_step_no_params():
    result = parse_vsl_stimulus("WRITE")
    assert result == [{"action": "WRITE", "params": {}}]


def test_single_step_with_hex_and_decimal_params():
    result = parse_vsl_stimulus("WRITE,addr=0x00,data=0xFF")
    assert result == [{"action": "WRITE", "params": {"addr": "0x00", "data": "0xFF"}}]

    result2 = parse_vsl_stimulus("WAIT,cycles=10")
    assert result2 == [{"action": "WAIT", "params": {"cycles": "10"}}]


def test_multi_step_sequence():
    vsl = "WRITE,addr=0x00,data=0x01;WAIT,cycles=10;READ,addr=0x04,expect=0x01"
    result = parse_vsl_stimulus(vsl)
    assert result == [
        {"action": "WRITE", "params": {"addr": "0x00", "data": "0x01"}},
        {"action": "WAIT",  "params": {"cycles": "10"}},
        {"action": "READ",  "params": {"addr": "0x04", "expect": "0x01"}},
    ]


def test_malformed_empty_param_raises():
    with pytest.raises(ValueError, match="empty param"):
        parse_vsl_stimulus("WRITE,,addr=0x00")


def test_malformed_param_missing_equals_raises():
    with pytest.raises(ValueError, match="no '='"):
        parse_vsl_stimulus("WRITE,addr")


def test_malformed_invalid_action_raises():
    with pytest.raises(ValueError, match="invalid action"):
        parse_vsl_stimulus("123BAD,addr=0x00")


def test_realistic_balu_axi_lite_uart_scenario():
    # COV-001: BAUD_TUNING — write NCO tuning word, wait for baud clock,
    # verify TX idle, then read status register to confirm lock.
    vsl = (
        "WRITE,addr=0x08,data=0x000010D6;"  # NCO_TUNING_WORD = 115200 baud divisor
        "WAIT,cycles=256;"
        "READ,addr=0x0C,expect=0x01"        # STATUS.BAUD_LOCKED = 1
    )
    result = parse_vsl_stimulus(vsl)
    assert len(result) == 3
    assert result[0] == {"action": "WRITE", "params": {"addr": "0x08", "data": "0x000010D6"}}
    assert result[1] == {"action": "WAIT",  "params": {"cycles": "256"}}
    assert result[2] == {"action": "READ",  "params": {"addr": "0x0C", "expect": "0x01"}}
