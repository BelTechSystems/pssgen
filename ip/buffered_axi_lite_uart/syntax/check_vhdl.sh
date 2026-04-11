#!/usr/bin/env bash
# DUT VHDL syntax check — no simulator license required.
# Checks: ip/buffered_axi_lite_uart/vhdl/buffered_axi_lite_uart.vhd
# Tool:   ghdl (must be on PATH)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VHD_FILE="$(cd "$SCRIPT_DIR/../vhdl" && pwd)/buffered_axi_lite_uart.vhd"
ghdl -a --std=08 "$VHD_FILE"
echo "VHDL syntax OK"
