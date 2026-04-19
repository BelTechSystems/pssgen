# ==============================================================
# File       : smoke.tcl
# Brief      : Smoke-only build — buffered_axi_lite_uart_test (single seq).
#              Recompiles everything fresh, logs to xsim_smoke.log.
# Usage      : vivado -mode tcl -source smoke.tcl
# ==============================================================
set DESIGN   buffered_axi_lite_uart
set SNAPSHOT balu_smoke_snapshot

set SCRIPT_DIR [file normalize [file dirname [info script]]]
set REPO_ROOT  [file normalize [file join $SCRIPT_DIR ../../../../../]]
set TB_DIR     [file join $REPO_ROOT output/balu_ral_session2/tb]
set RTL_DIR    [file join $REPO_ROOT ip/buffered_axi_lite_uart/vhdl]

puts "REPO_ROOT : $REPO_ROOT"
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

puts "\n--- Step 1: Compiling TB interface ---"
run_cmd [list xvlog --sv --uvm_version 1.2 -L uvm --work work \
    [file join $TB_DIR balu_axi_if.sv]]

puts "\n--- Step 2: Compiling DUT (VHDL 2008) ---"
run_cmd [list xvhdl --2008 --work work \
    [file join $RTL_DIR buffered_axi_lite_uart.vhd]]

puts "\n--- Step 3: Compiling TB package and tb_top ---"
run_cmd [list xvlog --sv --uvm_version 1.2 -L uvm --work work \
    --include $TB_DIR \
    --include $REPO_ROOT \
    [file join $TB_DIR ${DESIGN}_pkg.sv] \
    [file join $TB_DIR tb_top.sv]]

puts "\n--- Step 4: Elaborating ---"
run_cmd [list xelab -L uvm \
    work.tb_top \
    -s $SNAPSHOT \
    -timescale 1ns/1ps \
    -debug typical]

puts "\n--- Step 5: Smoke test (buffered_axi_lite_uart_test) ---"
run_cmd [list xsim $SNAPSHOT \
    -testplusarg UVM_TESTNAME=${DESIGN}_smoke_test \
    -testplusarg UVM_VERBOSITY=UVM_LOW \
    -runall \
    -log xsim_smoke.log]

puts "\nSmoke test complete. Log: xsim_smoke.log"
