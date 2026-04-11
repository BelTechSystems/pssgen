Icarus Verilog simulation — future target.

Blocker: Icarus has no bundled UVM library. A third-party
UVM implementation is required (Accellera uvm-core or equivalent).
Once a UVM library is available:
  iverilog -g2012 -DUVMLIB -f uvm.f -o sim.vvp <dut>.sv <tb_files>.sv
  vvp sim.vvp

DUT syntax-only checks (no UVM needed): see syntax/
Note: iverilog -g2012 -t null is used for DUT syntax only.
It cannot check UVM testbench files without the UVM library.
