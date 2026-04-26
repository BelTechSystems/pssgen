# ===========================================================
# FILE:         tests/test_sim_runner.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Unit tests for agents/sim_runner.py. Verifies TCL generation,
#   unsupported simulator handling, vivado_bin validation, state
#   manager integration, and output file placement.
#
# LAYER:        Tests
# PHASE:        D-035
#
# HISTORY:
#   D-035  2026-04-25  SB  Initial implementation; 10 sim_runner tests
#
# ===========================================================
"""Unit tests for the sim_runner simulator integration module."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import toml

from agents.sim_runner import generate_build_cov_tcl, parse_xcrg_results, run_simulate

# ---------------------------------------------------------------------------
# Minimal build.tcl content used by TCL generation tests
# ---------------------------------------------------------------------------

_MINIMAL_BUILD_TCL = """\
set DESIGN up_down_counter
run_cmd [list xelab \\
    -debug typical]
run_cmd [list xsim \\
    -log xsim.log]
puts "Simulation complete. Log: xsim.log"
"""


def _write_build_tcl(directory: str, content: str = _MINIMAL_BUILD_TCL) -> str:
    path = os.path.join(directory, "build.tcl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _write_pssgen_toml(directory: str, tool: str = "vivado", vivado_bin: str = "") -> str:
    path = os.path.join(directory, "pssgen.toml")
    config: dict = {"project": {"name": "test_ip"}, "simulator": {"tool": tool}}
    if vivado_bin:
        config["simulator"]["vivado_bin"] = vivado_bin
    with open(path, "w", encoding="utf-8") as fh:
        toml.dump(config, fh)
    return path


# ---------------------------------------------------------------------------
# generate_build_cov_tcl tests
# ---------------------------------------------------------------------------


def test_generate_build_cov_tcl_adds_cov_db_name(tmp_path) -> None:
    """build_cov.tcl contains the xelab -cov_db_name flag."""
    build_tcl = _write_build_tcl(str(tmp_path))
    out = generate_build_cov_tcl(build_tcl)
    content = open(out, encoding="utf-8").read()
    assert "-cov_db_name ${DESIGN}_cov" in content


def test_generate_build_cov_tcl_adds_cov_db_dir(tmp_path) -> None:
    """build_cov.tcl contains the xsim -cov_db_dir flag."""
    build_tcl = _write_build_tcl(str(tmp_path))
    out = generate_build_cov_tcl(build_tcl)
    content = open(out, encoding="utf-8").read()
    assert "-cov_db_dir ./coverage_db" in content


def test_generate_build_cov_tcl_adds_xcrg_call(tmp_path) -> None:
    """build_cov.tcl contains an xcrg invocation after the simulation step."""
    build_tcl = _write_build_tcl(str(tmp_path))
    out = generate_build_cov_tcl(build_tcl)
    content = open(out, encoding="utf-8").read()
    assert "xcrg" in content
    assert "coverage_db" in content


def test_generate_build_cov_tcl_no_overwrite_original(tmp_path) -> None:
    """Original build.tcl is unchanged after generate_build_cov_tcl."""
    build_tcl = _write_build_tcl(str(tmp_path))
    original = open(build_tcl, encoding="utf-8").read()
    generate_build_cov_tcl(build_tcl)
    after = open(build_tcl, encoding="utf-8").read()
    assert original == after


def test_generate_build_cov_tcl_preserves_design_name(tmp_path) -> None:
    """build_cov.tcl retains the set DESIGN line from build.tcl."""
    build_tcl = _write_build_tcl(str(tmp_path))
    out = generate_build_cov_tcl(build_tcl)
    content = open(out, encoding="utf-8").read()
    assert "set DESIGN" in content


def test_build_cov_tcl_written_to_correct_location(tmp_path) -> None:
    """build_cov.tcl is written alongside build.tcl, not elsewhere."""
    build_tcl = _write_build_tcl(str(tmp_path))
    out = generate_build_cov_tcl(build_tcl)
    expected = os.path.join(str(tmp_path), "build_cov.tcl")
    assert os.path.abspath(out) == os.path.abspath(expected)
    assert os.path.isfile(expected)


# ---------------------------------------------------------------------------
# run_simulate tests
# ---------------------------------------------------------------------------


def test_unsupported_simulator_returns_cleanly(tmp_path, capsys) -> None:
    """run_simulate returns success=False for modelsim/questa/icarus without raising."""
    for tool in ("modelsim", "questa", "icarus"):
        toml_path = _write_pssgen_toml(str(tmp_path), tool=tool)
        result = run_simulate(str(tmp_path), toml_path)
        assert result["success"] is False
        assert result["simulator"] == tool


def test_missing_vivado_bin_returns_error(tmp_path, capsys) -> None:
    """run_simulate returns success=False when vivado_bin is missing or invalid."""
    toml_path = _write_pssgen_toml(str(tmp_path), tool="vivado", vivado_bin="/nonexistent/path")
    result = run_simulate(str(tmp_path), toml_path)
    assert result["success"] is False
    captured = capsys.readouterr()
    assert "Vivado not found" in captured.out or "not found" in captured.out.lower()


def test_vivado_bin_from_pssgen_toml(tmp_path) -> None:
    """run_simulate reads vivado_bin from pssgen.toml [simulator] section."""
    fake_bin = os.path.join(str(tmp_path), "fake_vivado_bin")
    os.makedirs(fake_bin)
    toml_path = _write_pssgen_toml(str(tmp_path), tool="vivado", vivado_bin=fake_bin)
    result = run_simulate(str(tmp_path), toml_path)
    # vivado exe not present in fake bin → should fail cleanly, not raise
    assert result["success"] is False
    assert result["simulator"] == "vivado"


def test_state_updated_after_simulate(tmp_path) -> None:
    """run_simulate updates pssgen_state.toml via state_manager on success."""
    fake_bin = os.path.join(str(tmp_path), "vivado_bin")
    os.makedirs(fake_bin)
    fake_exe = os.path.join(fake_bin, "vivado.bat" if sys.platform == "win32" else "vivado")
    open(fake_exe, "w").close()

    scripts_dir = os.path.join(str(tmp_path), "tb", "scripts", "vivado")
    os.makedirs(scripts_dir, exist_ok=True)
    _write_build_tcl(scripts_dir)

    toml_path = _write_pssgen_toml(str(tmp_path), tool="vivado", vivado_bin=fake_bin)

    mock_proc = MagicMock()
    mock_proc.communicate.return_value = ("Simulation complete.\n", None)
    mock_proc.returncode = 0

    with patch("agents.sim_runner.subprocess.Popen", return_value=mock_proc):
        result = run_simulate(str(tmp_path), toml_path)

    assert result["success"] is True

    state_path = os.path.join(str(tmp_path), "pssgen_state.toml")
    assert os.path.isfile(state_path)
    state = toml.load(state_path)
    assert state["simulator"]["tool"] == "vivado"
    assert state["simulator"]["coverage_dir"] != ""


# ---------------------------------------------------------------------------
# parse_xcrg_results tests
# ---------------------------------------------------------------------------


def test_parse_xcrg_functional_coverage(tmp_path) -> None:
    """parse_xcrg_results extracts functional_coverage_pct from dashboard.html."""
    func_dir = os.path.join(str(tmp_path), "html", "functionalCoverageReport")
    os.makedirs(func_dir, exist_ok=True)
    with open(os.path.join(func_dir, "dashboard.html"), "w", encoding="utf-8") as fh:
        fh.write("<html><body><td>Score</td><td>41.6667</td></body></html>")

    result = parse_xcrg_results(str(tmp_path))
    assert result["functional_coverage_pct"] == pytest.approx(41.6667)


def test_parse_xcrg_covergroups(tmp_path) -> None:
    """parse_xcrg_results returns non-empty covergroups list from groups.html."""
    func_dir = os.path.join(str(tmp_path), "html", "functionalCoverageReport")
    os.makedirs(func_dir, exist_ok=True)
    # groups.html uses anchor-tag format as emitted by actual xcrg
    with open(os.path.join(func_dir, "groups.html"), "w", encoding="utf-8") as fh:
        fh.write(
            "<html><body><table>"
            '<tr><td><a href="grp0.html"> axi_transaction_cg</a></td>'
            "<td>41.6667</td></tr>"
            "</table></body></html>"
        )
    # grp0.html provides bin counts via Instance Variable Summary (Variables row)
    with open(os.path.join(func_dir, "grp0.html"), "w", encoding="utf-8") as fh:
        fh.write(
            "<html><body><table>"
            "<tr><td>3</td><td>Variables</td><td>24</td><td>14</td><td>10</td></tr>"
            "</table></body></html>"
        )

    result = parse_xcrg_results(str(tmp_path))
    assert len(result["covergroups"]) > 0
    assert result["covergroups"][0]["name"] == "axi_transaction_cg"
    assert result["covergroups"][0]["expected"] == 24
    assert result["covergroups"][0]["covered"] == 10


def test_parse_xcrg_missing_code_coverage(tmp_path) -> None:
    """code_coverage_pct is None when codeCoverageReport directory is absent."""
    result = parse_xcrg_results(str(tmp_path))
    assert result["code_coverage_pct"] is None


def test_vivado_coverage_results_json_written(tmp_path) -> None:
    """run_simulate writes vivado_coverage_results.json after successful simulation."""
    fake_bin = os.path.join(str(tmp_path), "vivado_bin")
    os.makedirs(fake_bin)
    fake_exe = os.path.join(fake_bin, "vivado.bat" if sys.platform == "win32" else "vivado")
    open(fake_exe, "w").close()

    scripts_dir = os.path.join(str(tmp_path), "tb", "scripts", "vivado")
    os.makedirs(scripts_dir, exist_ok=True)
    _write_build_tcl(scripts_dir)

    toml_path = _write_pssgen_toml(str(tmp_path), tool="vivado", vivado_bin=fake_bin)

    mock_proc = MagicMock()
    mock_proc.communicate.return_value = ("Simulation complete.\n", None)
    mock_proc.returncode = 0

    mock_xcrg = {
        "functional_coverage_pct": 41.67,
        "covergroups": [
            {"name": "axi_transaction_cg", "score": 41.67, "expected": 24, "covered": 10}
        ],
        "code_coverage_pct": None,
        "report_dir": "",
        "parsed_at": "2026-04-25T00:00:00+00:00",
    }

    with patch("agents.sim_runner.subprocess.Popen", return_value=mock_proc):
        with patch("agents.sim_runner.parse_xcrg_results", return_value=mock_xcrg):
            result = run_simulate(str(tmp_path), toml_path)

    assert result["success"] is True
    json_path = os.path.join(str(tmp_path), "coverage", "vivado_coverage_results.json")
    assert os.path.isfile(json_path)
    data = json.load(open(json_path, encoding="utf-8"))
    assert data["functional_coverage_pct"] == pytest.approx(41.67)
    assert "covergroups" in data
    assert data["simulator"] == "vivado"
