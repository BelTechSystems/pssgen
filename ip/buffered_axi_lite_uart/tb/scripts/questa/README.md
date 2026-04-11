Questa simulation — future target.

UVM library: Questa ships with UVM pre-compiled.
Compile DUT and TB with:
  vlog -sv -work work +acc <dut>.sv
  vlog -sv -uvm -work work +acc <tb_files>.sv
Simulate:
  vsim -c work.<top>_test -do "run -all; quit"

DUT syntax-only checks (no Questa needed): see syntax/
