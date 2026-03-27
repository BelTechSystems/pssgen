# Copyright (c) 2026 BelTech Systems LLC
# MIT License — see LICENSE file for details
"""tests/test_e2e.py — End-to-end v0 gate test.

Requires: ANTHROPIC_API_KEY environment variable.
Run with: pytest tests/test_e2e.py -v
Skip in CI without key: pytest -m "not e2e"
"""

import os
import subprocess
from pathlib import Path

import pytest

from orchestrator import JobSpec, run


pytestmark = pytest.mark.e2e


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_e2e_counter_vivado(tmp_path: Path) -> None:
    """Run full v0 pipeline and validate generated artifacts.

    Full pipeline: counter.v -> UVM scaffold -> xvlog compiles clean.

    This is the v0 definition-of-done test. It calls the real LLM and requires
    Vivado xvlog to be on PATH for the tier-2 syntax check. If xvlog is not
    available the test validates that 7 output files were generated and that
    the orchestrator run succeeded.

    Args:
        tmp_path: Pytest-provided temporary directory for output artifacts.
    """
    job = JobSpec(
        input_file="tests/fixtures/counter.v",
        top_module="up_down_counter",
        out_dir=str(tmp_path),
        sim_target="vivado",
        max_retries=3,
        no_llm=False,
        verbose=False,
    )

    result = run(job)

    assert result.success is True
    assert len(result.output_files) == 7

    expected = {
        "up_down_counter_if.sv",
        "up_down_counter_driver.sv",
        "up_down_counter_monitor.sv",
        "up_down_counter_seqr.sv",
        "up_down_counter_agent.sv",
        "up_down_counter_test.sv",
        "build.tcl",
    }
    actual = {Path(path).name for path in result.output_files}
    assert actual == expected

    try:
        subprocess.run(["xvlog", "--version"], capture_output=True, text=True, check=False)
        xvlog_available = True
    except FileNotFoundError:
        xvlog_available = False

    if xvlog_available:
        sv_files = sorted(str(path) for path in tmp_path.glob("*.sv"))
        proc = subprocess.run(
            ["xvlog", "--sv", "--nolog", *sv_files],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
