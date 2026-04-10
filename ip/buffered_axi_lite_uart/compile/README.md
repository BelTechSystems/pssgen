Source file syntax verification — no simulator
license required.
VHDL: ghdl -a --std=08 ../vhdl/buffered_axi_lite_uart.vhd
SV:   iverilog -g2012 -t null ../sv/buffered_axi_lite_uart.sv
Run these before every commit touching HDL files.
