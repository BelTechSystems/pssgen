set DESIGN   buffered_axi_lite_uart
set SNAPSHOT ${DESIGN}_snapshot

set SCRIPT_DIR [file dirname [file normalize [info script]]]
set TB_DIR     [file join $SCRIPT_DIR ../..]
set DUT_DIR    [file join $SCRIPT_DIR ../../..]

proc run_cmd {cmd} {
    if {[catch {exec {*}$cmd >@stdout 2>@stderr} msg]} {
        puts "ERROR: Command failed:"
        puts "  $cmd"
        puts $msg
        exit 1
    }
}

puts "--- Compiling DUT ---"
run_cmd [list xvhdl --2008 --work work \
    [file join $DUT_DIR vhdl/${DESIGN}.vhd]]

puts "--- Compiling UVM TB ---"
run_cmd [list xvlog --sv --uvm_version 1.2 -L uvm --work work \
    --include $TB_DIR \
    [file join $TB_DIR ${DESIGN}_if.sv] \
    [file join $TB_DIR ${DESIGN}_pkg.sv] \
    [file join $TB_DIR tb_top.sv]]

puts "--- Elaborating ---"
run_cmd [list xelab -L uvm \
    work.tb_top \
    -s $SNAPSHOT \
    -timescale 1ns/1ps \
    -debug typical \
    -cov_db_name ${DESIGN}_cov]

puts "--- Simulating ---"
run_cmd [list xsim $SNAPSHOT \
    -testplusarg UVM_TESTNAME=${DESIGN}_regression_test \
    -runall \
    -log xsim.log \
    -cov_db_dir ./coverage_db]

puts "Simulation complete. Log: xsim.log"
puts "--- Collecting coverage ---"
run_cmd [list xcrg \
    -cov_db_dir ./coverage_db \
    -cov_db_name ${DESIGN}_cov \
    -report_dir ./coverage_db/html \
    -report_format html]
puts "Coverage report written to ./coverage_db/html"
puts "--- Collecting code coverage ---"
run_cmd [list xcrg \
    -cov_db_dir ./coverage_db \
    -cov_db_name ${DESIGN}_cov \
    -report_dir ./coverage_db/html/codeCoverageReport \
    -report_format html]
puts "Code coverage report written to ./coverage_db/html/codeCoverageReport"
exit 0
