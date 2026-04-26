# ===========================================================
# FILE:         docs/dashboard/dashboard.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Streamlit verification dashboard for the pssgen BALU IP block.
#   Reads gap_report.json and vivado_coverage_results.json from GitHub
#   and displays requirement coverage, simulation status, and VSL
#   sequence generation progress.
#
# LAYER:        5 — dashboard / reporting
# PHASE:        v4 / D-034
#
# DEPENDENCIES:
#   Standard library:  datetime
#   External:          streamlit, plotly, pandas, requests
#
# HISTORY:
#   D-034  2026-04-18  SB  Initial implementation
#   D-035  2026-04-25  SB  Remove self-assessed coverage; promote Vivado xcrg
#
# ===========================================================

import datetime
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

GAP_REPORT_URL = (
    "https://raw.githubusercontent.com/BelTechSystems/pssgen/main"
    "/ip/buffered_axi_lite_uart/gap_report.json"
)
VIVADO_COVERAGE_URL = (
    "https://raw.githubusercontent.com/BelTechSystems/pssgen/main"
    "/ip/buffered_axi_lite_uart/coverage/vivado_coverage_results.json"
)

st.set_page_config(
    page_title="pssgen — FPGA Verification Dashboard",
    page_icon="🔬",
    layout="wide",
)


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_gap_report() -> dict:
    r = requests.get(GAP_REPORT_URL, timeout=10)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def load_vivado_coverage() -> dict:
    try:
        r = requests.get(VIVADO_COVERAGE_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def fetch_data():
    # Reads gap_report.json and vivado_coverage_results.json
    gap = None
    gap_ok = True

    try:
        gap = load_gap_report()
    except Exception as exc:
        gap_ok = False
        st.error(f"Failed to load gap report from:\n{GAP_REPORT_URL}\n\n{exc}")

    vc = load_vivado_coverage()

    if not gap_ok:
        if st.button("Retry"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    return gap, vc


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("pssgen Dashboard")
st.sidebar.markdown("---")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("**Data sources**")
st.sidebar.markdown(f"[gap\\_report.json]({GAP_REPORT_URL})")
st.sidebar.markdown(f"[vivado\\_coverage\\_results.json]({VIVADO_COVERAGE_URL})")
st.sidebar.markdown("---")
st.sidebar.info("Data cached for up to 5 minutes")


# ── Load data ─────────────────────────────────────────────────────────────────

gap, vc = fetch_data()

sim = gap["sim_result"]
summary = gap["summary"]
families = gap["family_summary_array"]
requirements = gap["requirements"]

commit = gap.get("commit", "unknown")
generated = gap.get("generated", "")
st.sidebar.markdown(f"**Commit:** `{commit}`")


# ── Section 1: Header ─────────────────────────────────────────────────────────

st.title("pssgen — FPGA Verification Dashboard")
st.markdown("**Buffered AXI-Lite UART | BelTech Systems LLC**")

h_col1, h_col2, h_col3 = st.columns([3, 2, 2])
with h_col1:
    if generated:
        try:
            ts = datetime.datetime.fromisoformat(generated.replace("Z", "+00:00"))
            st.caption(f"Last updated: {ts.strftime('%Y-%m-%d %H:%M UTC')}")
        except ValueError:
            st.caption(f"Last updated: {generated}")
with h_col2:
    st.caption(f"Commit: `{commit}`")
with h_col3:
    st.markdown("[GitHub — BelTechSystems/pssgen](https://github.com/BelTechSystems/pssgen)")

st.markdown("---")


# ── Section 2: Simulation Result metrics ──────────────────────────────────────

st.subheader("Simulation Result")

m1, m2, m3, m4 = st.columns(4)

uvm_errors = sim.get("uvm_errors", 0)
uvm_fatals = sim.get("uvm_fatals", 0)
vc_pct = vc.get("functional_coverage_pct", 0.0) if vc else 0.0
passing = summary.get("passing", 0)
total = summary.get("total", 0)

with m1:
    err_delta = "✓ Clean" if uvm_errors == 0 else f"⚠ {uvm_errors} error(s)"
    st.metric("UVM Errors", uvm_errors, delta=err_delta,
              delta_color="normal" if uvm_errors == 0 else "inverse")

with m2:
    fat_delta = "✓ Clean" if uvm_fatals == 0 else f"⚠ {uvm_fatals} fatal(s)"
    st.metric("UVM Fatals", uvm_fatals, delta=fat_delta,
              delta_color="normal" if uvm_fatals == 0 else "inverse")

with m3:
    if vc_pct >= 95:
        cov_label = f"{vc_pct:.1f}% ✅"
    elif vc_pct >= 80:
        cov_label = f"{vc_pct:.1f}% ⚠️"
    else:
        cov_label = f"{vc_pct:.1f}% ❌"
    st.metric("Vivado Coverage", cov_label)
    st.caption("Vivado 2025.1 xcrg")

with m4:
    st.metric("Requirements Passing", f"{passing} / {total}")

st.markdown("---")


# ── Section 3: Vivado Coverage Detail ─────────────────────────────────────────

st.subheader("Vivado Coverage Results")

if vc:
    st.info(
        "Coverage source: Vivado 2025.1 xcrg — "
        "independently measured, not self-assessed."
    )

    _verdict_emoji = {
        "PRODUCTION_READY": "✅",
        "NEEDS_WORK": "⚠️",
        "CRITICAL_GAPS": "❌",
    }

    # Row 1 — four metrics
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.metric("Functional Coverage", f"{vc.get('functional_coverage_pct', 0.0):.1f}%")
    r1c2.metric("Effort Level", vc.get("effort_level", "—").upper())
    r1c3.metric(
        "Passes Run",
        f"{vc.get('passes_run', 0)} of {vc.get('max_passes', 0)}",
    )
    reached = vc.get("target_reached", False)
    r1c4.metric("Target Reached", "✅ Yes" if reached else "⚠️ No")

    # Row 2 — three metrics
    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("Target", f"{vc.get('target_pct', 0.0):.1f}%")
    vc_verdict = vc.get("verdict", "UNKNOWN")
    vc_emoji = _verdict_emoji.get(vc_verdict, "❓")
    r2c2.metric("Verdict", f"{vc_emoji} {vc_verdict}")
    r2c3.metric("Covergroups", len(vc.get("covergroups", [])))

    # Covergroup table
    covergroups = vc.get("covergroups", [])
    if covergroups:
        def _truncate_cg_name(name: str) -> str:
            parts = name.split("::")
            return "::".join(parts[-2:]) if len(parts) >= 2 else name

        cg_df = pd.DataFrame([
            {
                "Covergroup": _truncate_cg_name(cg["name"]),
                "Score": f"{cg['score']:.1f}%",
                "Expected": cg.get("expected", 0),
                "Covered": cg.get("covered", 0),
            }
            for cg in covergroups
        ])
        st.dataframe(cg_df, use_container_width=True, hide_index=True)
else:
    st.warning(
        "Vivado coverage results not available. Run --simulate to generate."
    )

st.markdown("---")


# ── Section 4: Requirements Coverage by Family ────────────────────────────────

st.subheader("Requirements Coverage by Family")

fam_col, tbl_col = st.columns([3, 2])

fam_names  = [f["family"].replace("UART-", "") for f in families]
fam_pass   = [f.get("passing", 0) for f in families]
fam_fail   = [f.get("failing", 0) for f in families]
fam_waived = [f.get("waived", 0)  for f in families]

with fam_col:
    fig = go.Figure(data=[
        go.Bar(name="Passing", x=fam_names, y=fam_pass,
               marker_color="#2ECC71"),
        go.Bar(name="Failing", x=fam_names, y=fam_fail,
               marker_color="#E74C3C"),
        go.Bar(name="Waived",  x=fam_names, y=fam_waived,
               marker_color="#F1C40F"),
    ])
    fig.update_layout(
        barmode="group",
        title="Requirements Coverage by Family",
        xaxis_title="Family",
        yaxis_title="Count",
        plot_bgcolor="#1A1F2E",
        paper_bgcolor="#1A1F2E",
        font_color="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

with tbl_col:
    fam_df = pd.DataFrame([
        {
            "Family":  f["family"],
            "Passing": f.get("passing", 0),
            "Failing": f.get("failing", 0),
            "Waived":  f.get("waived", 0),
            "Total":   f.get("passing", 0) + f.get("failing", 0) + f.get("waived", 0),
        }
        for f in families
    ])

    def _color_family_row(row):
        if row["Failing"] > 0:
            return ["background-color: #4A1010"] * len(row)
        return ["background-color: #0D3320"] * len(row)

    styled_fam = fam_df.style.apply(_color_family_row, axis=1)
    st.dataframe(styled_fam, use_container_width=True, hide_index=True)

st.markdown("---")


# ── Section 5: D-034 Phase 1 VSL Coverage ─────────────────────────────────────

with st.expander("D-034 Phase 1 — VSL Sequence Generation", expanded=True):
    try:
        _vsl_url = (
            "https://raw.githubusercontent.com/BelTechSystems/pssgen/main"
            "/ip/buffered_axi_lite_uart/results/balu_coverage_results.json"
        )
        _vsl_r = requests.get(_vsl_url, timeout=10)
        _vsl_r.raise_for_status()
        _cov = _vsl_r.json()
    except Exception:
        _cov = {}
    _cov_summary = _cov.get("summary", {})
    _goals = _cov.get("goals", [])

    d034_col, goals_col = st.columns([1, 2])

    with d034_col:
        st.metric("D-034 Phase", _cov.get("d034_phase", "—"))
        st.metric("WRITTEN",     _cov_summary.get("WRITTEN", 0))
        st.metric("APPROVED",    _cov_summary.get("APPROVED", 0))
        st.metric("VSL Coverage", f"{_cov_summary.get('coverage_pct', 0.0):.1f}%")
        st.metric("PHASE_2_GAP", _cov_summary.get("PHASE_2_GAP", 0))
        notes = _cov_summary.get("notes", "")
        if notes:
            st.caption(f"Notes: {notes}")

    with goals_col:
        if _goals:
            goals_df = pd.DataFrame([
                {
                    "COV ID":          g["id"],
                    "Name":            g["name"],
                    "Seq Status":      g["seq_status"],
                    "Coverage Status": g["coverage_status"],
                    "VSL Steps":       g.get("vsl_steps", 0),
                }
                for g in _goals
            ])

            def _color_goal_row(row):
                if row["Seq Status"] == "PHASE_1" and row["Coverage Status"] == "WRITTEN":
                    return ["background-color: #0D3320"] * len(row)
                if row["Seq Status"] == "PHASE_2_GAP":
                    return ["background-color: #3D3000"] * len(row)
                if row["Seq Status"] == "DRAFT":
                    return ["background-color: #3D1A00"] * len(row)
                return [""] * len(row)

            styled_goals = goals_df.style.apply(_color_goal_row, axis=1)
            st.dataframe(styled_goals, use_container_width=True, hide_index=True)
        else:
            st.info("VSL goal data not available.")

st.markdown("---")


# ── Section 6: Requirements Detail ────────────────────────────────────────────

with st.expander("Requirements Detail", expanded=False):
    search = st.text_input("Filter by Req ID or Family", key="req_filter")

    req_df = pd.DataFrame([
        {
            "Req ID":      r["req_id"],
            "Family":      r["family"],
            "Covered By":  r.get("covered_by", ""),
            "Disposition": r.get("disposition", ""),
            "RTL Status":  r.get("rtl_status", ""),
            "Overall":     r.get("overall_status", ""),
        }
        for r in requirements
    ]).sort_values("Family").reset_index(drop=True)

    if search:
        mask = (
            req_df["Req ID"].str.contains(search, case=False, na=False) |
            req_df["Family"].str.contains(search, case=False, na=False)
        )
        req_df = req_df[mask].reset_index(drop=True)

    def _color_req_row(row):
        status = row["Overall"]
        if status == "PASS":
            return ["background-color: #0D3320"] * len(row)
        if status == "FAIL":
            return ["background-color: #4A1010"] * len(row)
        if status in ("WAIVED", "WAIVE"):
            return ["background-color: #3D3000"] * len(row)
        return [""] * len(row)

    styled_req = req_df.style.apply(_color_req_row, axis=1)
    st.dataframe(styled_req, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(req_df)} of {len(requirements)} requirements")

st.markdown("---")


# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown(
    "MIT Licensed | Open Source | "
    "[github.com/BelTechSystems/pssgen](https://github.com/BelTechSystems/pssgen)"
)
st.caption(
    "Generated by pssgen — AI-driven FPGA verification environment generator"
)
