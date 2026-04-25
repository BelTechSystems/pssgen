import json
from datetime import datetime, timezone

def analyze_coverage(
    rtl_analysis_path,
    sim_coverage_path,
    gap_report_path,
    vplan_path=None,
    code_coverage_path=None,
    functional_coverage_path=None,
    assertion_coverage_path=None
):
    with open(sim_coverage_path) as f:
        sim = json.load(f)
    with open(gap_report_path) as f:
        gap = json.load(f)

    code_cov = {}
    if code_coverage_path:
        with open(code_coverage_path) as f:
            code_cov = json.load(f)

    func_cov = {}
    if functional_coverage_path:
        with open(functional_coverage_path) as f:
            func_cov = json.load(f)

    assert_cov = {}
    if assertion_coverage_path:
        with open(assertion_coverage_path) as f:
            assert_cov = json.load(f)

    address_pct = sim.get("coverage_pct", 0.0)
    branch_pct = code_cov.get("summary", {}).get(
        "branch_coverage_pct", 0.0)
    adjusted_branch_pct = code_cov.get("summary", {}).get(
        "adjusted_coverage_pct", 0.0)
    functional_pct = func_cov.get(
        "functional_coverage_pct", 0.0)
    assertion_pct = assert_cov.get(
        "adjusted_assertion_coverage_pct", 0.0)

    gaps = func_cov.get("gaps", [])
    easy_wins = [g for g in gaps
                 if g.get("effort_estimate") == "EASY"]
    medium_gaps = [g for g in gaps
                   if g.get("effort_estimate") == "MEDIUM"]
    hard_gaps = [g for g in gaps
                 if g.get("effort_estimate") == "HARD"]

    real_gaps = code_cov.get(
        "summary", {}).get("real_gaps", 0)
    high_risk = func_cov.get(
        "summary", {}).get("high_risk_gaps", 0)

    overall = round(
        (address_pct + branch_pct + functional_pct) / 3, 1)

    if overall >= 90 and high_risk == 0 and real_gaps <= 5:
        verdict = "PRODUCTION_READY"
    elif overall >= 80 and high_risk <= 2:
        verdict = "NEEDS_WORK"
    else:
        verdict = "CRITICAL_GAPS"

    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "coverage_metrics": {
            "address_coverage_pct": address_pct,
            "branch_coverage_pct": branch_pct,
            "adjusted_branch_pct": adjusted_branch_pct,
            "functional_coverage_pct": functional_pct,
            "assertion_coverage_pct": assertion_pct,
            "overall_pct": overall
        },
        "risk_matrix": {
            "high_risk_gaps": high_risk,
            "medium_risk_gaps": len(medium_gaps),
            "low_risk_gaps": func_cov.get(
                "summary", {}).get("low_risk_gaps", 0),
            "real_rtl_gaps": real_gaps,
            "phase2_gaps": func_cov.get(
                "summary", {}).get("phase2_gaps", 0)
        },
        "easy_wins": [
            {
                "req_id": g.get("req_id", ""),
                "family": g.get("family", ""),
                "covered_by": g.get("covered_by", ""),
                "seq_status": g.get("seq_status", ""),
                "recommended_action": g.get(
                    "recommended_action", ""),
                "effort": "EASY",
                "risk": g.get("risk_level", "")
            }
            for g in easy_wins
        ],
        "medium_gaps": medium_gaps,
        "hard_gaps": hard_gaps,
        "verdict": verdict,
        "verdict_rationale": (
            f"Overall {overall}% coverage. "
            f"{high_risk} high-risk gaps. "
            f"{real_gaps} real RTL branch gaps. "
            f"{len(easy_wins)} easy wins available."
        ),
        "summary": {
            "overall_pct": overall,
            "verdict": verdict,
            "easy_wins": len(easy_wins),
            "high_risk_gaps": high_risk,
            "real_rtl_gaps": real_gaps,
            "recommendation": (
                "Ready for production verification sign-off"
                if verdict == "PRODUCTION_READY"
                else "Address easy wins then re-assess"
                if verdict == "NEEDS_WORK"
                else "Critical gaps require immediate attention"
            )
        }
    }
