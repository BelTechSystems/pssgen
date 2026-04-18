# ===========================================================
# FILE:         docs/dashboard/dashboard.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Streamlit verification dashboard for the pssgen BALU IP block.
#   Reads gap_report.json and balu_coverage_results.json from GitHub
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
BALU_COVERAGE_URL = (
    "https://raw.githubusercontent.com/BelTechSystems/pssgen/main"
    "/ip/buffered_axi_lite_uart/results/balu_coverage_results.json"
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
def load_coverage_results() -> dict:
    r = requests.get(BALU_COVERAGE_URL, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_data():
    gap, cov = None, None
    gap_ok, cov_ok = True, True

    try:
        gap = load_gap_report()
    except Exception as exc:
        gap_ok = False
        st.error(f"Failed to load gap report from:\n{GAP_REPORT_URL}\n\n{exc}")

    try:
        cov = load_coverage_results()
    except Exception as exc:
        cov_ok = False
        st.error(f"Failed to load coverage results from:\n{BALU_COVERAGE_URL}\n\n{exc}")

    if not gap_ok or not cov_ok:
        if st.button("Retry"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    return gap, cov


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("pssgen Dashboard")
st.sidebar.markdown("---")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("**Data sources**")
st.sidebar.markdown(f"[gap\\_report.json]({GAP_REPORT_URL})")
st.sidebar.markdown(f"[balu\\_coverage\\_results.json]({BALU_COVERAGE_URL})")
st.sidebar.markdown("---")
st.sidebar.info("Data cached for up to 5 minutes")


# ── Load data ─────────────────────────────────────────────────────────────────

gap, cov = fetch_data()

sim = gap["sim_result"]
summary = gap["summary"]
families = gap["family_summary_array"]
requirements = gap["requirements"]
cov_summary = cov["summary"]
goals = cov["goals"]

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
cov_pct = sim.get("coverage_pct", 0.0)
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
    if cov_pct >= 80:
        cov_label = f"{cov_pct:.1f}% ✓"
    elif cov_pct >= 50:
        cov_label = f"{cov_pct:.1f}% ⚠"
    else:
        cov_label = f"{cov_pct:.1f}% ✗"
    st.metric("Functional Coverage", cov_label)

with m4:
    st.metric("Requirements Passing", f"{passing} / {total}")

st.markdown("---")


# ── Section 3: Coverage by Family ─────────────────────────────────────────────

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


# ── Section 4: D-034 Phase 1 VSL Coverage ─────────────────────────────────────

with st.expander("D-034 Phase 1 — VSL Sequence Generation", expanded=True):
    d034_col, goals_col = st.columns([1, 2])

    with d034_col:
        st.metric("D-034 Phase", cov.get("d034_phase", "—"))
        st.metric("WRITTEN",     cov_summary.get("WRITTEN", 0))
        st.metric("APPROVED",    cov_summary.get("APPROVED", 0))
        st.metric("VSL Coverage", f"{cov_summary.get('coverage_pct', 0.0):.1f}%")
        st.metric("PHASE_2_GAP", cov_summary.get("PHASE_2_GAP", 0))
        notes = cov_summary.get("notes", "")
        if notes:
            st.caption(f"Notes: {notes}")

    with goals_col:
        goals_df = pd.DataFrame([
            {
                "COV ID":          g["id"],
                "Name":            g["name"],
                "Seq Status":      g["seq_status"],
                "Coverage Status": g["coverage_status"],
                "VSL Steps":       g.get("vsl_steps", 0),
            }
            for g in goals
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

st.markdown("---")


# ── Section 5: Requirements Detail ────────────────────────────────────────────

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


# ── Section 6: Footer ─────────────────────────────────────────────────────────

st.markdown(
    "MIT Licensed | Open Source | "
    "[github.com/BelTechSystems/pssgen](https://github.com/BelTechSystems/pssgen)"
)
st.caption(
    "Generated by pssgen — AI-driven FPGA verification environment generator"
)
