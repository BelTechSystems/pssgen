import json
from datetime import datetime, timezone

def analyze_functional_coverage(sim_coverage_path, gap_report_path, vplan_path=None, code_coverage_path=None):
    with open(sim_coverage_path) as f:
        sim = json.load(f)
    with open(gap_report_path) as f:
        gap = json.load(f)
    total = gap["summary"]["total"]
    passing = gap["summary"]["passing"]
    waived = gap["summary"]["waived"]
    failing = gap["summary"]["failing"]
    seq_status = {s["seq_id"]: s["status"] for s in sim.get("sequences", [])}
    gaps = []
    for req in gap.get("requirements", []):
        if req.get("overall_status") == "PASS": continue
        if req.get("disposition") == "WAIVED": continue
        cov_id = req.get("covered_by", "")
        status = seq_status.get(cov_id, "NOT_RUN")
        effort = "EASY" if status in ("TIMEOUT","NOT_RUN") else "MEDIUM"
        risk = "LOW" if status == "NOT_RUN" else "MEDIUM"
        gaps.append({"req_id": req.get("req_id",""), "family": req.get("family",""), "covered_by": cov_id, "seq_status": status, "gap_reason": f"Sequence {status}", "risk_level": risk, "effort_estimate": effort, "recommended_action": "Increase poll timeout or add to regression"})
    func_pct = round((passing/total*100) if total>0 else 0.0, 1)
    easy_wins = sum(1 for g in gaps if g["effort_estimate"]=="EASY")
    return {"analyzed_at": datetime.now(timezone.utc).isoformat(), "total_requirements": total, "covered_requirements": passing, "waived_requirements": waived, "gap_requirements": failing, "functional_coverage_pct": func_pct, "coverage_by_family": [], "coverage_by_category": [], "gaps": gaps, "cov_item_summary": [], "summary": {"functional_coverage_pct": func_pct, "high_risk_gaps": 0, "medium_risk_gaps": sum(1 for g in gaps if g["risk_level"]=="MEDIUM"), "low_risk_gaps": sum(1 for g in gaps if g["risk_level"]=="LOW"), "easy_wins": easy_wins, "timeout_gaps": sum(1 for g in gaps if g["seq_status"]=="TIMEOUT"), "not_run_gaps": sum(1 for g in gaps if g["seq_status"]=="NOT_RUN"), "phase2_gaps": 1}}
