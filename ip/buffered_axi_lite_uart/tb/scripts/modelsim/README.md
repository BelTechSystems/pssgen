ModelSim simulation — future target.
Covers Intel FPGA Edition, Lattice Edition, Microchip Edition,
and standalone Siemens ModelSim. All share vsim/vlog syntax.

UVM library: availability depends on vendor and version.
  Intel FPGA Edition: UVM pre-compiled in $MODEL_TECH/../verilog_src/uvm-1.1d/
  Lattice/Microchip: check vendor documentation
  Standalone: install from Accellera uvm-core package
Compile DUT and TB:
  vlog -sv -work work <dut>.sv
  vlog -sv +incdir+$UVM_HOME/src $UVM_HOME/src/uvm_pkg.sv <tb_files>.sv
Simulate:
  vsim -c work.<top>_test -do "run -all; quit"

DUT syntax-only checks (no ModelSim needed): see syntax/
