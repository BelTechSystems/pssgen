Vivado XSIM simulation — batch mode, no GUI.

Requirements:
  Vivado 2024.x or later on PATH
  UVM: bundled with Vivado (--uvm flag, no separate install)
  Part: xczu1cg-sbva484-1-e (ZUBoard 1CG)

Run from this directory:
  vivado -mode tcl -source build.tcl

The script compiles the DUT (SV), compiles the UVM testbench
with Vivado's bundled UVM 1.2 library (--uvm flag), elaborates,
and runs simulation. Log written to xsim.log.

DUT syntax-only checks (no Vivado needed): see syntax/
