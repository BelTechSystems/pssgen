DUT source syntax verification — no simulator license required.
These scripts check only the DUT source files (vhdl/ and sv/).
They do NOT check the UVM testbench — use tb/scripts/<tool>/ for that.

VHDL:  bash check_vhdl.sh    (requires ghdl on PATH)
SV:    bash check_sv.sh      (requires iverilog on PATH)

These run automatically on every commit via .git/hooks/pre-commit.
UVM testbench syntax is checked via:
  tb/scripts/vivado/ — xvlog --uvm (requires Vivado on PATH)
