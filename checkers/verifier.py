# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""checkers/verifier.py — Three-tier artifact verifier.

Phase: v0
Layer: 4 (checkers)

Validates generated artifacts with structural checks, optional simulator syntax
checks, and smoke checks while preserving a stable checker contract.
"""
from dataclasses import dataclass
from agents.structure_gen import Artifact
import re, subprocess, os, tempfile


@dataclass
class CheckResult:
    """Checker response payload.

    Attributes:
        passed: Whether validation passed.
        tier: Tier index that produced this result.
        reason: Failure reason or informational message.
    """
    passed: bool
    tier: int
    reason: str


def check(artifacts: list[Artifact], sim_target: str = "vivado") -> CheckResult:
    """Run checker tiers in order until failure or completion.

    Args:
        artifacts: Generated output artifacts to validate.
        sim_target: Simulator target used for tier-2 syntax invocation.

    Returns:
        CheckResult from the first failing tier or final passing tier.
    """
    result = _tier1_structural(artifacts)
    if not result.passed:
        return result

    result = _tier2_syntax(artifacts, sim_target)
    if not result.passed:
        return result

    result = _tier3_smoke(artifacts)
    return result


# ── Tier 1: structural checks (no simulator required) ─────────────────

_REQUIRED = {
    "_driver.sv":    ["uvm_component_utils", "build_phase", "run_phase"],
    "_monitor.sv":   ["uvm_component_utils", "write("],
    "_agent.sv":     ["uvm_component_utils", "build_phase"],
    "_if.sv":        ["interface"],
    "_seqr.sv":      ["uvm_component_utils"],
    "_test.sv":      ["uvm_component_utils"],
}


def _tier1_structural(artifacts: list[Artifact]) -> CheckResult:
    for artifact in artifacts:
        for suffix, required_strings in _REQUIRED.items():
            if artifact.filename.endswith(suffix):
                for req in required_strings:
                    if req not in artifact.content:
                        return CheckResult(
                            passed=False,
                            tier=1,
                            reason=f"{artifact.filename}: missing '{req}'"
                        )
    return CheckResult(passed=True, tier=1, reason="")


# ── Tier 2: syntax check (calls xvlog or vlog) ────────────────────────

def _tier2_syntax(artifacts: list[Artifact], sim_target: str) -> CheckResult:
    sv_files = [a for a in artifacts if a.filename.endswith(".sv")]
    if not sv_files:
        return CheckResult(passed=True, tier=2, reason="no sv files to check")

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = []
        for a in sv_files:
            p = os.path.join(tmpdir, a.filename)
            with open(p, "w") as f:
                f.write(a.content)
            paths.append(p)

        if sim_target == "vivado":
            cmd = ["xvlog", "--sv", "--nolog"] + paths
        else:
            cmd = ["vlog", "-quiet"] + paths

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                return CheckResult(
                    passed=False, tier=2,
                    reason=proc.stderr or proc.stdout or "compiler error"
                )
        except FileNotFoundError:
            # Simulator not installed — skip tier 2 gracefully
            pass

    return CheckResult(passed=True, tier=2, reason="")


# ── Tier 3: smoke checks ──────────────────────────────────────────────

def _tier3_smoke(artifacts: list[Artifact]) -> CheckResult:
    names = {a.filename for a in artifacts}
    if not any("build" in n for n in names):
        return CheckResult(passed=False, tier=3, reason="no build script generated")
    return CheckResult(passed=True, tier=3, reason="")
