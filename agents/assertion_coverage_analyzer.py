import json
from datetime import datetime, timezone

def analyze_assertion_coverage(rtl_analysis_path, sim_coverage_path):
    with open(rtl_analysis_path) as f:
        rtl = json.load(f)
    with open(sim_coverage_path) as f:
        sim = json.load(f)
    rtl_assertions = rtl.get("assertions", [])
    fired = {a["message"]: a for a in sim.get("assertions_fired", [])}
    results = []
    for a in rtl_assertions:
        cond = a.get("condition", "")
        matched = next((f for f in fired.values()
                       if cond[:20] in f.get("message","")), None)
        if matched:
            status = ("FIRED_FAILURE"
                     if matched.get("severity","") == "error"
                     else "FIRED_OK")
            classification = "ACTIVE"
            time_ns = matched.get("time_ns", 0.0)
        else:
            status = "NEVER_FIRED"
            time_ns = 0.0
            classification = ("DEAD_CODE"
                             if a.get("severity","") == "failure"
                             else "UNTESTED")
        results.append({
            "assertion_id": a.get("assertion_id",""),
            "condition": cond,
            "severity": a.get("severity",""),
            "line_number": a.get("line_number", 0),
            "status": status,
            "classification": classification,
            "time_ns": time_ns
        })
    total = len(results)
    n_fired = sum(1 for r in results if r["status"] != "NEVER_FIRED")
    n_failures = sum(1 for r in results
                    if r["status"] == "FIRED_FAILURE")
    n_dead = sum(1 for r in results
                if r["classification"] == "DEAD_CODE")
    n_untested = sum(1 for r in results
                    if r["classification"] == "UNTESTED")
    pct = round((n_fired/total*100) if total > 0 else 0.0, 1)
    adj_total = total - n_dead
    adj_pct = round((n_fired/(adj_total)*100)
                   if adj_total > 0 else 100.0, 1)
    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "total_assertions": total,
        "fired": n_fired,
        "never_fired": total - n_fired,
        "failures": n_failures,
        "dead_code": n_dead,
        "untested": n_untested,
        "assertion_coverage_pct": pct,
        "adjusted_assertion_coverage_pct": adj_pct,
        "assertions": results
    }
