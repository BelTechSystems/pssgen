# ==============================================================
# File       : build.tcl
# Project    : pssgen — AI-Driven PSS + UVM + C Testbench Generator
# Copyright  : Copyright (c) 2026 BelTech Systems LLC
# License    : MIT License — see LICENSE for details
# ==============================================================
# Brief      : buffered_axi_lite_uart RAL Session 3 — five-step
#              Vivado/XSIM build and regression script.
# Document   : BelTech-STD-003 Rev 1
# Tool       : Vivado 2024.x / XSIM
#
# Usage (from this directory):
#   vivado -mode tcl -source build.tcl
# Or via xsim standalone flow:
#   tclsh build.tcl   (if tclsh knows xvhdl/xvlog/xelab/xsim)
#
# Compile order:
#   1. axi4_lite_if.sv   — interface (standalone, before bfm_pkg)
#   2. bfm_pkg.sv        — BFM package (`include brings in all class files)
#   3. DUT VHDL          — buffered_axi_lite_uart.vhd (VHDL 2008)
#   4. TB pkg + tb_top   — buffered_axi_lite_uart_pkg.sv + tb_top.sv
#   5. xelab + xsim      — elaborate and run regression
#
# Impl. status   : generated-ral
#
# History:
#   2026-04-18  pssgen  RAL Session 3: corrected paths, active DUT compile
# ==============================================================
set DESIGN   buffered_axi_lite_uart
set SNAPSHOT balu_sim_snapshot

# ── Path anchors — all relative to this script's location (scripts/vivado) ────
set SCRIPT_DIR [file normalize [file dirname [info script]]]
set REPO_ROOT  [file normalize [file join $SCRIPT_DIR ../../../../../]]
set SIM_LIB    [file join $REPO_ROOT sim/lib]
set TB_DIR     [file join $REPO_ROOT output/balu_ral_session2/tb]
set RTL_DIR    [file join $REPO_ROOT ip/buffered_axi_lite_uart/vhdl]

puts "REPO_ROOT : $REPO_ROOT"
puts "SIM_LIB   : $SIM_LIB"
puts "TB_DIR    : $TB_DIR"
puts "RTL_DIR   : $RTL_DIR"

proc run_cmd {cmd} {
    puts "CMD: [join $cmd { }]"
    if {[catch {exec {*}$cmd >@stdout 2>@stderr} msg]} {
        puts "ERROR: Command failed:"
        puts $msg
        exit 1
    }
}

# ── Step 1: Compile TB-local non-parameterized AXI interface ──────────────────
# balu_axi_if.sv is a non-parameterized wrapper for the 32-bit AXI4-Lite bus.
# axi4_lite_if is parameterized; using it as a virtual interface config_db type
# triggers EXCEPTION_ACCESS_VIOLATION in xelab 2025.1.
# bfm_pkg.sv is NOT compiled — its classes are inlined in the TB package.
puts "\n--- Step 1: Compiling TB interface ---"
run_cmd [list xvlog --sv --uvm_version 1.2 -L uvm --work work \
    [file join $TB_DIR balu_axi_if.sv]]

# ── Step 2: Compile DUT (VHDL 2008) ───────────────────────────────────────────
# buffered_axi_lite_uart.vhd uses IEEE std_logic_1164 / numeric_std only.
puts "\n--- Step 2: Compiling DUT (VHDL 2008) ---"
run_cmd [list xvhdl --2008 --work work \
    [file join $RTL_DIR buffered_axi_lite_uart.vhd]]

# ── Step 3: Compile TB package and top ────────────────────────────────────────
# buffered_axi_lite_uart_pkg.sv `include-s all TB class files.
# --include $TB_DIR resolves un-pathed `include "*.sv" directives.
# --include $REPO_ROOT resolves any cross-repo includes.
puts "\n--- Step 3: Compiling TB package and tb_top ---"
run_cmd [list xvlog --sv --uvm_version 1.2 -L uvm --work work \
    --include $TB_DIR \
    --include $REPO_ROOT \
    [file join $TB_DIR ${DESIGN}_pkg.sv] \
    [file join $TB_DIR tb_top.sv]]

# ── Step 4: Elaborate ─────────────────────────────────────────────────────────
puts "\n--- Step 4: Elaborating ---"
run_cmd [list xelab -L uvm \
    work.tb_top \
    -s $SNAPSHOT \
    -timescale 1ns/1ps \
    -debug typical]

# ── Step 5: Simulate — run full regression ────────────────────────────────────
puts "\n--- Step 5: Simulating regression ---"
run_cmd [list xsim $SNAPSHOT \
    -testplusarg UVM_TESTNAME=${DESIGN}_regression_test \
    -testplusarg UVM_VERBOSITY=UVM_LOW \
    -runall \
    -log xsim.log]

puts "\nSimulation complete. Log: xsim.log"
