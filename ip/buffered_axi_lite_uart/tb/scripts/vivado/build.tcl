# =============================================================
# File    : tb/scripts/vivado/build.tcl
# IP      : buffered_axi_lite_uart
# Tool    : Vivado XSIM (batch mode, no GUI, no project)
# Vivado  : 2024.x or later
# UVM     : 1.2 (Vivado bundled — --uvm flag on xvlog)
# Run     : vivado -mode tcl -source build.tcl
#           (from tb/scripts/vivado/ directory)
# Note    : --uvm on xvlog links Vivado's bundled UVM 1.2 library.
#           Without it every uvm_* reference is undefined.
# =============================================================

set DESIGN   buffered_axi_lite_uart
set SNAPSHOT ${DESIGN}_snapshot

# Paths relative to this script's location
set SCRIPT_DIR [file dirname [file normalize [info script]]]
set TB_DIR     [file join $SCRIPT_DIR ../..]
set DUT_DIR    [file join $SCRIPT_DIR ../../..]

# --- Step 1: Compile DUT ---
# DUT compile — language determined from pssgen.toml [[sources]]
puts "Compiling DUT..."

exec xvhdl --2008 --work work \
  [file join $DUT_DIR buffered_axi_lite_uart.vhd] \
  >@stdout 2>@stderr


# --- Step 2: Compile UVM testbench (--uvm links bundled UVM 1.2) ---
puts "Compiling UVM testbench..."
exec xvlog --sv --uvm --work work \
  [file join $TB_DIR ${DESIGN}_if.sv]     \
  [file join $TB_DIR ${DESIGN}_agent.sv]  \
  [file join $TB_DIR ${DESIGN}_driver.sv] \
  [file join $TB_DIR ${DESIGN}_monitor.sv] \
  [file join $TB_DIR ${DESIGN}_seqr.sv]   \
  [file join $TB_DIR ${DESIGN}_test.sv]   \
  >@stdout 2>@stderr

# --- Step 3: Elaborate ---
puts "Elaborating..."
exec xelab -L uvm \
  work.${DESIGN}_test \
  work.glbl \
  -s $SNAPSHOT \
  -timescale 1ns/1ps \
  >@stdout 2>@stderr

# --- Step 4: Simulate ---
puts "Simulating..."
exec xsim $SNAPSHOT -runall -log xsim.log \
  >@stdout 2>@stderr

puts "Done. Log: tb/scripts/vivado/xsim.log"