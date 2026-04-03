# ===========================================================
# FILE:         checkers/verifier.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Three-tier artifact validator. Tier 1 checks structural requirements
#   (UVM macros, phases, PSS keywords) without a simulator. Tier 2 invokes
#   xvlog or vlog for syntax validation, skipping gracefully if absent.
#   Tier 3 checks that a build script is present. Checker contract is frozen.
#
# LAYER:        4 — checkers
# PHASE:        v0
#
# FUNCTIONS:
#   check(artifacts, sim_target)
#     Run all checker tiers in order; return CheckResult from first failure or final pass.
#
# DEPENDENCIES:
#   Standard library:  dataclasses, re, subprocess, os, tempfile
#   Internal:          agents.structure_gen
#
# HISTORY:
#   v0    2026-03-27  SB  Initial implementation; structural and smoke tiers
#   v1b   2026-03-27  SB  Added PSS structural validation tier
#   v4b   2026-04-03  SB  Added _tier1_ral_structural for reg_block/pkg/seq artifacts; utf-8 temp files
#
# ===========================================================
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

    for artifact in artifacts:
        if artifact.filename.endswith(".pss"):
            design_name = os.path.splitext(os.path.basename(artifact.filename))[0]
            result = _tier1_pss_structural(artifact, design_name)
            if not result.passed:
                return result

    _RAL_SUFFIXES = ("_reg_block.sv", "_reg_pkg.sv", "_reg_seq.sv")
    for artifact in artifacts:
        if any(artifact.filename.endswith(s) for s in _RAL_SUFFIXES):
            # Derive design_name from the artifact filename
            dn = artifact.filename
            for s in _RAL_SUFFIXES:
                if dn.endswith(s):
                    dn = dn[: -len(s)]
                    break
            result = _tier1_ral_structural(artifact, dn)
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
    # OI-10 (SDS): PSS elaboration/parser tier is deferred because no
    # pip-installable open-source PSS parser is available for integration.
    # OI-11: C artifact tier-2 syntax check — deferred.
    # Future: call gcc --syntax-only on .c artifacts.
    # Requires gcc on PATH. Skip gracefully if absent.
    # .c files are intentionally excluded here; they are not validated by
    # xvlog/vlog and have no structural UVM checks in any tier.
    sv_files = [a for a in artifacts if a.filename.endswith(".sv")]
    if not sv_files:
        return CheckResult(passed=True, tier=2, reason="no sv files to check")

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = []
        for a in sv_files:
            p = os.path.join(tmpdir, a.filename)
            with open(p, "w", encoding="utf-8") as f:
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


def _tier1_pss_structural(artifact: Artifact, design_name: str) -> CheckResult:
    """Validate minimum structural requirements for a generated PSS model.

    Args:
        artifact: PSS artifact under validation.
        design_name: Expected design/component stem name.

    Returns:
        Tier-1 CheckResult for PSS structural validity.
    """
    required = ["component", "action", design_name]
    for req in required:
        if req not in artifact.content:
            return CheckResult(
                passed=False,
                tier=1,
                reason=f"{artifact.filename}: missing '{req}'",
            )
    return CheckResult(passed=True, tier=1, reason="")


def _tier1_ral_structural(artifact: Artifact, design_name: str) -> CheckResult:
    """Tier-1 structural check for UVM RAL artifacts.

    Verifies minimum required content is present without invoking any
    external tool.

    Args:
        artifact: The generated RAL artifact to validate.
        design_name: Design name expected in the artifact content.

    Returns:
        CheckResult with passed=True or a descriptive reason on failure.
    """
    fname = artifact.filename

    if fname.endswith("_reg_block.sv"):
        required = [
            "extends uvm_reg_block",
            "extends uvm_reg",
            "create_map",
            "add_reg",
            design_name,
        ]
    elif fname.endswith("_reg_pkg.sv"):
        required = ["package", "import uvm_pkg", design_name]
    elif fname.endswith("_reg_seq.sv"):
        # Either sequence base class is acceptable
        has_seq = (
            "extends uvm_reg_sequence" in artifact.content
            or "extends uvm_reg_hw_reset_seq" in artifact.content
        )
        if not has_seq:
            return CheckResult(
                passed=False,
                tier=1,
                reason=(
                    f"{fname}: missing 'extends uvm_reg_sequence' or "
                    "'extends uvm_reg_hw_reset_seq'"
                ),
            )
        required = [design_name]
    else:
        return CheckResult(passed=True, tier=1, reason="")

    for req in required:
        if req not in artifact.content:
            return CheckResult(
                passed=False,
                tier=1,
                reason=f"{fname}: missing '{req}'",
            )
    return CheckResult(passed=True, tier=1, reason="")
