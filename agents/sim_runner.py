# ===========================================================
# FILE:         agents/sim_runner.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Simulator integration layer for the --simulate CLI flag. Generates
#   build_cov.tcl (coverage-enabled variant of build.tcl) and drives
#   Vivado in Tcl batch mode. Streams simulation output to the terminal
#   in real time, collects the coverage database path after xcrg runs,
#   and updates pssgen_state.toml via state_manager. Unsupported simulator
#   targets (modelsim, questa, icarus) return cleanly without error.
#
# LAYER:        3 — agents
# PHASE:        D-035
#
# FUNCTIONS:
#   generate_build_cov_tcl(build_tcl_path)
#     Inject coverage flags into build.tcl; write build_cov.tcl.
#   run_simulate(ip_dir, pssgen_toml_path)
#     Drive full Vivado simulation with coverage collection.
#
# DEPENDENCIES:
#   Standard library:  datetime, os, re, subprocess
#   Internal:          agents.state_manager
#   Third-party:       toml
#
# HISTORY:
#   D-035  2026-04-25  SB  Initial implementation; Vivado coverage flow
#
# ===========================================================
"""agents/sim_runner.py — Simulator integration for --simulate CLI flag."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

import toml

_UNSUPPORTED_TOOLS = {"modelsim", "questa", "icarus"}
_VIVADO_BIN_CANDIDATES = ("vivado.exe", "vivado")

# ── TCL snippets injected into the coverage build script ──────────────

_XCRG_BLOCK = (
    '\nputs "--- Collecting coverage ---"\n'
    "run_cmd [list xcrg \\\n"
    "    -report_format html \\\n"
    "    -dir ./coverage_db/${DESIGN}_cov.covdb \\\n"
    "    -output ./coverage_db/html]\n"
    'puts "Coverage report written to ./coverage_db/html"'
)


def generate_build_cov_tcl(build_tcl_path: str) -> str:
    """Read existing build.tcl, inject coverage flags, write build_cov.tcl.

    Makes three targeted changes only:
      1. xelab gains ``-cov_db_name ${DESIGN}_cov``
      2. xsim gains ``-cov_db_dir ./coverage_db``
      3. xcrg invocation appended after the "Simulation complete." line

    The original build.tcl is never modified.

    Args:
        build_tcl_path: Absolute or relative path to the existing build.tcl.

    Returns:
        Path to the written build_cov.tcl file.
    """
    with open(build_tcl_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # 1. Add coverage DB name to xelab
    content = content.replace(
        "    -debug typical]",
        "    -debug typical \\\n    -cov_db_name ${DESIGN}_cov]",
    )

    # 2. Add coverage DB dir to xsim
    content = content.replace(
        "    -log xsim.log]",
        "    -log xsim.log \\\n    -cov_db_dir ./coverage_db]",
    )

    # 3. Append xcrg call after the final "Simulation complete." line
    sim_complete_line = 'puts "Simulation complete. Log: xsim.log"'
    content = content.replace(
        sim_complete_line,
        sim_complete_line + _XCRG_BLOCK,
    )

    out_dir = os.path.dirname(os.path.abspath(build_tcl_path))
    out_path = os.path.join(out_dir, "build_cov.tcl")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    return out_path


def _find_vivado_exe(vivado_bin: str) -> str | None:
    """Return path to vivado executable inside vivado_bin, or None."""
    for name in _VIVADO_BIN_CANDIDATES:
        candidate = os.path.join(vivado_bin, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _parse_vivado_version(log_path: str) -> str:
    """Extract version string from Vivado log header (e.g. '2025.1')."""
    if not os.path.isfile(log_path):
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                match = re.search(r"Vivado v(\S+)", line)
                if match:
                    return match.group(1)
    except OSError:
        pass
    return ""


def run_simulate(ip_dir: str, pssgen_toml_path: str) -> dict[str, Any]:
    """Drive Vivado simulation with coverage collection.

    Reads simulator configuration from pssgen.toml, validates the Vivado
    binary path, generates build_cov.tcl alongside the existing build.tcl,
    and runs ``vivado -mode tcl -source build_cov.tcl`` from the
    tb/scripts/vivado/ working directory. Streams output to stdout in real
    time. Updates pssgen_state.toml on completion.

    Unsupported simulator targets (modelsim, questa, icarus) emit a single
    informational message and return ``success=False`` without raising.

    Args:
        ip_dir: Root directory of the IP block (contains pssgen.toml).
        pssgen_toml_path: Absolute path to pssgen.toml.

    Returns:
        Dict with keys: success, simulator, version, coverage_dir,
        xsim_log, vivado_log.
    """
    with open(pssgen_toml_path, "r", encoding="utf-8") as fh:
        config = toml.load(fh)

    sim_cfg = config.get("simulator", {})
    tool: str = sim_cfg.get("tool", "vivado")

    _empty: dict[str, Any] = {
        "success": False,
        "simulator": tool,
        "version": "",
        "coverage_dir": "",
        "xsim_log": "",
        "vivado_log": "",
    }

    if tool in _UNSUPPORTED_TOOLS:
        print(
            f"Coverage assessment requires Vivado. "
            f"{tool} simulation not yet supported."
        )
        return dict(_empty)

    if tool != "vivado":
        print(
            f"Coverage assessment requires Vivado. "
            f"{tool} simulation not yet supported."
        )
        return dict(_empty)

    vivado_bin: str = sim_cfg.get("vivado_bin", "")
    if not vivado_bin or not os.path.isdir(vivado_bin):
        print(
            f"Vivado not found at {vivado_bin!r}. "
            "Check pssgen.toml [simulator] vivado_bin."
        )
        return dict(_empty)

    vivado_exe = _find_vivado_exe(vivado_bin)
    if vivado_exe is None:
        print(
            f"Vivado executable not found in {vivado_bin!r}. "
            "Check pssgen.toml [simulator] vivado_bin."
        )
        return dict(_empty)

    scripts_dir = os.path.join(ip_dir, "tb", "scripts", "vivado")
    build_tcl = os.path.join(scripts_dir, "build.tcl")
    generate_build_cov_tcl(build_tcl)

    vivado_log = os.path.join(scripts_dir, "vivado.log")
    xsim_log = os.path.join(scripts_dir, "xsim.log")
    coverage_dir = os.path.join(scripts_dir, "coverage_db", "html")

    try:
        proc = subprocess.Popen(
            [vivado_exe, "-mode", "tcl", "-source", "build_cov.tcl"],
            cwd=scripts_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
        proc.wait()
        success = proc.returncode == 0
    except OSError as exc:
        print(f"[sim_runner] Vivado launch failed: {exc}")
        return dict(_empty)

    version = _parse_vivado_version(vivado_log)

    # Update pssgen_state.toml — best-effort; never raises
    try:
        from agents.state_manager import load_state, save_state

        state = load_state(ip_dir)
        state["simulator"]["tool"] = "vivado"
        state["simulator"]["version"] = version
        state["simulator"]["xcrg_path"] = os.path.join(vivado_bin, "xcrg").replace("\\", "/")
        state["simulator"]["coverage_dir"] = coverage_dir.replace("\\", "/")
        state["project"]["last_run"] = datetime.now(timezone.utc).isoformat()
        save_state(ip_dir, state)
    except Exception:  # noqa: BLE001
        pass

    return {
        "success": success,
        "simulator": "vivado",
        "version": version,
        "coverage_dir": coverage_dir,
        "xsim_log": xsim_log,
        "vivado_log": vivado_log,
    }
