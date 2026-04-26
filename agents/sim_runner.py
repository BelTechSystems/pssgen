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
#   Vivado in Tcl batch mode. After simulation, parses xcrg HTML reports
#   for functional and code coverage percentages, writes
#   vivado_coverage_results.json, and updates pssgen_state.toml.
#   Unsupported simulator targets return cleanly without error.
#
# LAYER:        3 — agents
# PHASE:        D-035
#
# FUNCTIONS:
#   generate_build_cov_tcl(build_tcl_path)
#     Inject coverage flags into build.tcl; write build_cov.tcl.
#   parse_xcrg_results(coverage_db_dir)
#     Parse xcrg HTML reports; return coverage pct and covergroup details.
#   run_simulate(ip_dir, pssgen_toml_path)
#     Drive full Vivado simulation with coverage collection and closeout.
#
# DEPENDENCIES:
#   Standard library:  datetime, json, os, re, subprocess, sys
#   Internal:          agents.state_manager
#   Third-party:       toml
#
# HISTORY:
#   D-035  2026-04-25  SB  Initial implementation; Vivado coverage flow
#   D-035  2026-04-25  SB  xcrg parser, code coverage flags, closeout
#   D-035  2026-04-26  SB  xsim_cov.tcl; tclbatch; xsim.codeCov path
#
# ===========================================================
"""agents/sim_runner.py — Simulator integration for --simulate CLI flag."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

import toml

_UNSUPPORTED_TOOLS = {"modelsim", "questa", "icarus"}
_VIVADO_BIN_CANDIDATES = ("vivado.bat",) if sys.platform == "win32" else ("vivado",)

# ── TCL snippets injected into the coverage build script ──────────────

_XCRG_BLOCK = (
    '\nputs "--- Collecting coverage ---"\n'
    "run_cmd [list xcrg \\\n"
    "    -cov_db_dir ./coverage_db \\\n"
    "    -cov_db_name ${DESIGN}_cov \\\n"
    "    -report_dir ./coverage_db/html \\\n"
    "    -report_format html]\n"
    'puts "Coverage report written to ./coverage_db/html"'
)

_CODE_COV_BLOCK = (
    '\nputs "--- Collecting code coverage ---"\n'
    "run_cmd [list xcrg \\\n"
    "    -cov_db_dir ./coverage_db/xsim.codeCov \\\n"
    "    -cov_db_name ${DESIGN}_cov \\\n"
    "    -report_dir ./coverage_db/html/codeCoverageReport \\\n"
    "    -report_format html]\n"
    'puts "Code coverage report written to ./coverage_db/html/codeCoverageReport"'
)

_XSIM_COV_TCL_TEMPLATE = (
    "run -all\n"
    "write_xsim_coverage \\\n"
    "    -cov_db_dir ./coverage_db \\\n"
    "    -cov_db_name {design_name}_cov\n"
    "exit\n"
)


def generate_build_cov_tcl(build_tcl_path: str) -> str:
    """Read existing build.tcl, inject coverage flags, write build_cov.tcl.

    Makes five targeted changes:
      1. xelab gains ``-cov_db_name ${DESIGN}_cov``
      2. xsim gains ``-cov_db_dir ./coverage_db``
      3. Functional xcrg invocation appended after "Simulation complete."
      4. Code coverage xcrg invocation appended after functional xcrg
      5. ``exit 0`` appended to prevent Vivado hanging at prompt

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

    # 2. Replace -runall with -tclbatch so xsim sources xsim_cov.tcl instead
    content = content.replace(
        "    -runall \\\n",
        "    -tclbatch xsim_cov.tcl \\\n",
    )

    # 3. Add coverage DB dir to xsim
    content = content.replace(
        "    -log xsim.log]",
        "    -log xsim.log \\\n    -cov_db_dir ./coverage_db]",
    )

    # 4+5. Append functional then code coverage xcrg calls after sim complete
    sim_complete_line = 'puts "Simulation complete. Log: xsim.log"'
    content = content.replace(
        sim_complete_line,
        sim_complete_line + _XCRG_BLOCK + _CODE_COV_BLOCK,
    )

    # 6. Ensure Vivado exits cleanly
    content += "\nexit 0\n"

    out_dir = os.path.dirname(os.path.abspath(build_tcl_path))
    out_path = os.path.join(out_dir, "build_cov.tcl")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    # 7. Write xsim_cov.tcl — sourced by xsim via -tclbatch; runs sim and
    #    writes code coverage database before exiting.
    design_match = re.search(r"set\s+DESIGN\s+(\S+)", content)
    design_name = design_match.group(1) if design_match else "design"
    xsim_cov_path = os.path.join(out_dir, "xsim_cov.tcl")
    with open(xsim_cov_path, "w", encoding="utf-8") as fh:
        fh.write(_XSIM_COV_TCL_TEMPLATE.format(design_name=design_name))

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


def _parse_coverage_pct(html_path: str) -> float:
    """Extract coverage percentage from an xcrg dashboard.html file."""
    if not os.path.isfile(html_path):
        return 0.0
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        m = re.search(r"Score.*?(\d+\.?\d*)", html, re.DOTALL | re.IGNORECASE)
        if m:
            return float(m.group(1))
    except OSError:
        pass
    return 0.0


def parse_xcrg_results(coverage_db_dir: str) -> dict[str, Any]:
    """Parse xcrg HTML reports to extract coverage percentages and covergroup details.

    Reads the functionalCoverageReport and codeCoverageReport subdirectories
    under coverage_db_dir/html/. Missing files are handled gracefully.

    Args:
        coverage_db_dir: Path to the coverage_db directory (parent of html/).

    Returns:
        Dict with keys: functional_coverage_pct, covergroups, code_coverage_pct,
        report_dir, parsed_at.
    """
    html_dir = os.path.join(coverage_db_dir, "html")
    func_report = os.path.join(html_dir, "functionalCoverageReport")
    code_report = os.path.join(html_dir, "codeCoverageReport")

    functional_pct = _parse_coverage_pct(os.path.join(func_report, "dashboard.html"))

    covergroups: list[dict[str, Any]] = []
    groups_path = os.path.join(func_report, "groups.html")
    if os.path.isfile(groups_path):
        try:
            with open(groups_path, "r", encoding="utf-8", errors="replace") as fh:
                html = fh.read()
            for m in re.finditer(
                r'<td>\s*<a href="(grp\d+\.html)">\s*(.*?)\s*</a></td>'
                r"\s*<td[^>]*>\s*(\d+\.?\d*)\s*</td>",
                html,
                re.DOTALL,
            ):
                grp_href, name, score_str = m.group(1), m.group(2), m.group(3)
                expected, covered = 0, 0
                grp_path = os.path.join(func_report, grp_href)
                if os.path.isfile(grp_path):
                    with open(grp_path, "r", encoding="utf-8", errors="replace") as gfh:
                        grp_html = gfh.read()
                    vm = re.search(
                        r"<td[^>]*>Variables</td>\s*<td[^>]*>\s*(\d+)\s*</td>"
                        r"\s*<td[^>]*>\s*\d+\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>",
                        grp_html,
                        re.DOTALL,
                    )
                    if vm:
                        expected, covered = int(vm.group(1)), int(vm.group(2))
                covergroups.append(
                    {
                        "name": name,
                        "score": float(score_str),
                        "expected": expected,
                        "covered": covered,
                    }
                )
        except OSError:
            pass

    code_pct: float | None = None
    code_dashboard = os.path.join(code_report, "dashboard.html")
    if os.path.isfile(code_dashboard):
        val = _parse_coverage_pct(code_dashboard)
        code_pct = val if val > 0.0 else None

    return {
        "functional_coverage_pct": functional_pct,
        "covergroups": covergroups,
        "code_coverage_pct": code_pct,
        "report_dir": html_dir,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
    }


def run_simulate(ip_dir: str, pssgen_toml_path: str) -> dict[str, Any]:
    """Drive Vivado simulation with coverage collection.

    Reads simulator configuration from pssgen.toml, validates the Vivado
    binary path, generates build_cov.tcl alongside the existing build.tcl,
    and runs ``vivado -mode tcl -source build_cov.tcl`` from the
    tb/scripts/vivado/ working directory. Parses xcrg HTML reports after
    completion and writes vivado_coverage_results.json. Updates
    pssgen_state.toml on completion.

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
    coverage_db_dir = os.path.join(scripts_dir, "coverage_db")
    coverage_dir = os.path.join(coverage_db_dir, "html")

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
        stdout_data, _ = proc.communicate(timeout=1800)
        print(stdout_data, end="")
        success = proc.returncode == 0
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        print("[pssgen] ERROR: Vivado timed out after 30 minutes.")
        return dict(_empty)
    except OSError as exc:
        print(f"[sim_runner] Vivado launch failed: {exc}")
        return dict(_empty)

    version = _parse_vivado_version(vivado_log)

    # Parse xcrg HTML reports — best-effort; defaults on missing files
    xcrg = parse_xcrg_results(coverage_db_dir)

    # Write vivado_coverage_results.json
    try:
        from agents.state_manager import load_state

        state = load_state(ip_dir)
        effort = state.get("effort", {})
        effort_level = effort.get("level", "low")
        target_pct = float(effort.get("target_pct", 95.0))
        max_passes = {"low": 1, "medium": 3, "high": 5}.get(effort_level, 1)
        func_pct = xcrg["functional_coverage_pct"]
        target_reached = func_pct >= target_pct

        if func_pct >= 90.0:
            verdict = "PRODUCTION_READY"
        elif func_pct >= 80.0:
            verdict = "NEEDS_WORK"
        else:
            verdict = "CRITICAL_GAPS"

        coverage_source = f"Vivado {version} xcrg" if version else "Vivado xcrg"
        cov_results = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "simulator": "vivado",
            "version": version,
            "coverage_source": coverage_source,
            "effort_level": effort_level,
            "passes_run": 1,
            "max_passes": max_passes,
            "target_pct": target_pct,
            "target_reached": target_reached,
            "functional_coverage_pct": func_pct,
            "code_coverage_pct": xcrg["code_coverage_pct"],
            "covergroups": xcrg["covergroups"],
            "verdict": verdict,
            "coverage_note": (
                f"Coverage measured by {coverage_source}. Not self-assessed."
            ),
        }
        cov_out_dir = os.path.join(ip_dir, "coverage")
        os.makedirs(cov_out_dir, exist_ok=True)
        cov_json_path = os.path.join(cov_out_dir, "vivado_coverage_results.json")
        with open(cov_json_path, "w", encoding="utf-8") as fh:
            json.dump(cov_results, fh, indent=2)
    except Exception:  # noqa: BLE001
        cov_json_path = ""
        verdict = "UNKNOWN"
        func_pct = xcrg.get("functional_coverage_pct", 0.0)
        coverage_source = f"Vivado {version} xcrg" if version else "Vivado xcrg"

    # Print closeout
    print("[pssgen] Simulation complete.")
    print(f"[pssgen] Functional coverage: {func_pct:.1f}% ({coverage_source})")
    if xcrg.get("code_coverage_pct") is not None:
        print(f"[pssgen] Code coverage: {xcrg['code_coverage_pct']:.1f}%")
    if cov_json_path:
        print(f"[pssgen] Results: {cov_json_path}")

    # Update pssgen_state.toml — best-effort; never raises
    try:
        from agents.state_manager import load_state, save_state

        xcrg_name = "xcrg.bat" if sys.platform == "win32" else "xcrg"
        state = load_state(ip_dir)
        state["simulator"]["tool"] = "vivado"
        state["simulator"]["version"] = version
        state["simulator"]["xcrg_path"] = os.path.join(vivado_bin, xcrg_name).replace("\\", "/")
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
