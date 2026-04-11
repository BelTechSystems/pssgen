#!/usr/bin/env bash
# DUT SystemVerilog syntax check — no simulator license required.
# Checks: ip/buffered_axi_lite_uart/sv/buffered_axi_lite_uart.sv
# Tool:   iverilog (must be on PATH)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
iverilog -g2012 -t null "$SCRIPT_DIR/../sv/buffered_axi_lite_uart.sv"
echo "SV syntax OK"
