import json
import os
import pytest

COVERAGE_DIR = "ip/buffered_axi_lite_uart/coverage"
IP_DIR = "ip/buffered_axi_lite_uart"

def load(filename):
    path = os.path.join(COVERAGE_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def test_rtl_analysis_exists():
    assert os.path.exists(
        os.path.join(COVERAGE_DIR, "rtl_analysis.json"))

def test_sim_coverage_exists():
    assert os.path.exists(
        os.path.join(COVERAGE_DIR, "sim_coverage.json"))

def test_code_coverage_exists():
    assert os.path.exists(
        os.path.join(COVERAGE_DIR, "code_coverage.json"))

def test_functional_coverage_exists():
    assert os.path.exists(
        os.path.join(COVERAGE_DIR,
            "functional_coverage.json"))

def test_assertion_coverage_exists():
    assert os.path.exists(
        os.path.join(COVERAGE_DIR,
            "assertion_coverage.json"))

def test_coverage_assessment_exists():
    assert os.path.exists(
        os.path.join(COVERAGE_DIR,
            "coverage_assessment.json"))

def test_coverage_report_exists():
    assert os.path.exists(
        os.path.join(IP_DIR,
            "coverage_assessment.md"))

def test_rtl_analysis_schema():
    d = load("rtl_analysis.json")
    for key in ["total_branches", "processes",
                "branches", "assertions", "summary"]:
        assert key in d

def test_sim_coverage_schema():
    d = load("sim_coverage.json")
    for key in ["uvm_counts", "coverage_pct",
                "sequences", "scoreboard"]:
        assert key in d

def test_code_coverage_schema():
    d = load("code_coverage.json")
    for key in ["total_branches", "branch_coverage_pct",
                "summary", "branches"]:
        assert key in d

def test_assertion_coverage_schema():
    d = load("assertion_coverage.json")
    for key in ["total_assertions", "fired",
                "dead_code", "assertions"]:
        assert key in d

def test_coverage_assessment_schema():
    d = load("coverage_assessment.json")
    for key in ["coverage_metrics", "risk_matrix",
                "verdict", "summary"]:
        assert key in d

def test_rtl_branches_count():
    d = load("rtl_analysis.json")
    assert d["total_branches"] >= 100

def test_sim_coverage_pct_positive():
    d = load("sim_coverage.json")
    assert d["coverage_pct"] > 0.0

def test_code_branch_coverage_range():
    d = load("code_coverage.json")
    pct = d["branch_coverage_pct"]
    assert 0.0 <= pct <= 100.0

def test_assertion_dead_code_count():
    d = load("assertion_coverage.json")
    assert d["dead_code"] == 5

def test_verdict_valid_value():
    d = load("coverage_assessment.json")
    assert d["verdict"] in [
        "PRODUCTION_READY",
        "NEEDS_WORK",
        "CRITICAL_GAPS"
    ]

def test_report_utf8_readable():
    path = os.path.join(IP_DIR, "coverage_assessment.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "# BALU Coverage Assessment Report" in content
    assert "Verdict" in content

def test_report_contains_metrics():
    path = os.path.join(IP_DIR, "coverage_assessment.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Address Coverage" in content
    assert "Branch Coverage" in content
    assert "Functional Coverage" in content

def test_cae_module_imports():
    from agents.rtl_analyzer import analyze_vhdl
    from agents.code_coverage_analyzer import \
        analyze_code_coverage
    from agents.functional_coverage_analyzer import \
        analyze_functional_coverage
    from agents.assertion_coverage_analyzer import \
        analyze_assertion_coverage
    from agents.coverage_analyzer import analyze_coverage
    from agents.report_generator import \
        generate_coverage_report
    assert True
