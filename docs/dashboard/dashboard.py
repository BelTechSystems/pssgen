# ===========================================================
# FILE:         docs/dashboard/dashboard.py
# PROJECT:      pssgen — AI-Driven PSS + UVM + C Testbench Generator
# COPYRIGHT:    Copyright (c) 2026 BelTech Systems LLC
# LICENSE:      MIT License — see LICENSE file for details
# ===========================================================
#
# DESCRIPTION:
#   Streamlit verification dashboard for the pssgen BALU IP block.
#   Reads gap_report.json and vivado_coverage_results.json from GitHub.
#   Vivado xcrg is the sole authoritative coverage source — no
#   self-assessed coverage data is displayed.
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
#   D-036  2026-04-26  SB  Full overhaul: two-column status, remove legacy sources
#   D-037  2026-04-27  SB  Coverage Detail: functional/code/weighted panels, 12-CG table
#   D-038  2026-04-27  SB  Remove VSL Sequence Generation expander; fetch_data returns gap only
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
    gap = None
    gap_ok = True

    try:
        gap = load_gap_report()
    except Exception as exc:
        gap_ok = False
        st.error(f"Failed to load gap report from:\n{GAP_REPORT_URL}\n\n{exc}")

    if not gap_ok:
        if st.button("Retry"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    return gap


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

gap = fetch_data()
vc = load_vivado_coverage()

sim = gap["sim_result"]
summary = gap["summary"]
families = gap["family_summary_array"]
requirements = gap["requirements"]

commit = gap.get("commit", "unknown")
generated = gap.get("generated", "")

st.sidebar.caption(f"Commit: {commit}")


# ── Section 1: Header ─────────────────────────────────────────────────────────

st.title("pssgen — FPGA Verification Dashboard")
st.markdown("**Buffered AXI-Lite UART | BelTech Systems LLC**")

h_col1, h_col2 = st.columns([3, 2])
with h_col1:
    if generated:
        try:
            ts = datetime.datetime.fromisoformat(generated.replace("Z", "+00:00"))
            st.caption(f"Last updated: {ts.strftime('%Y-%m-%d %H:%M UTC')}")
        except ValueError:
            st.caption(f"Last updated: {generated}")
with h_col2:
    st.markdown("[GitHub — BelTechSystems/pssgen](https://github.com/BelTechSystems/pssgen)")

st.markdown("---")


# ── Section 2: Verification Status ────────────────────────────────────────────

st.subheader("Verification Status")

uvm_errors = sim.get("uvm_errors", 0)
uvm_fatals = sim.get("uvm_fatals", 0)
vc_pct = vc.get("functional_coverage_pct", 0.0) if vc else 0.0
passing = summary.get("passing", 0)
total = summary.get("total", 0)

left_col, right_col = st.columns(2)

with left_col:
    err_delta = "✓ Clean" if uvm_errors == 0 else f"⚠ {uvm_errors} error(s)"
    st.metric("UVM Errors", uvm_errors, delta=err_delta,
              delta_color="normal" if uvm_errors == 0 else "inverse")

    fat_delta = "✓ Clean" if uvm_fatals == 0 else f"⚠ {uvm_fatals} fatal(s)"
    st.metric("UVM Fatals", uvm_fatals, delta=fat_delta,
              delta_color="normal" if uvm_fatals == 0 else "inverse")

    st.metric("Requirements", f"{passing} / {total}")

    if vc_pct >= 95:
        cov_delta_color = "normal"
    elif vc_pct >= 80:
        cov_delta_color = "off"
    else:
        cov_delta_color = "inverse"
    st.metric("Functional Coverage", f"{vc_pct:.1f}%",
              delta="Vivado 2025.1 xcrg", delta_color=cov_delta_color)

with right_col:
    if vc:
        sim_label = f"{vc.get('simulator', '').title()} {vc.get('version', '')}".strip()
    else:
        sim_label = "—"
    st.metric("Simulator", sim_label or "—")
    st.metric("Coverage Tool", "xcrg")
    st.metric("Effort Level", vc.get("effort_level", "—").upper() if vc else "—")
    passes_str = (
        f"{vc.get('passes_run', 0)} of {vc.get('max_passes', 0)}" if vc else "—"
    )
    st.metric("Passes Run", passes_str)

st.markdown("---")


# ── Section 3: Requirements Coverage by Family ────────────────────────────────

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


# ── Section 4: Requirements Detail ────────────────────────────────────────────

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


# ── Section 6: Verification Coverage Detail ───────────────────────────────────

_COVERGROUP_VPR_FAMILY = {
    "axi_transaction_cg":  "IF",
    "baud_rate_cg":        "BR",
    "uart_enable_cg":      "EN",
    "parity_cg":           "PAR",
    "stop_bits_cg":        "PAR",
    "fifo_threshold_cg":   "FIFO",
    "timeout_cg":          "TO",
    "interrupt_enable_cg": "INT",
    "interrupt_clear_cg":  "INT",
    "reset_values_cg":     "RST",
    "ro_access_cg":        "FF",
    "error_response_cg":   "IF",
}


def _truncate_cg_name(name: str) -> str:
    parts = name.split("::")
    return "::".join(parts[-2:]) if len(parts) >= 2 else name


def _fc_delta(pct: float):
    if pct >= 95:
        return "✓ On target", "normal"
    if pct >= 80:
        return "⚠ Below target", "off"
    return "✗ Needs work", "inverse"


def _cc_delta(pct: float):
    if pct >= 80:
        return "✓", "normal"
    if pct >= 50:
        return "⚠", "off"
    return "✗", "inverse"


with st.expander("Verification Coverage Detail", expanded=True):
    if not vc:
        st.warning("Vivado coverage results not available. Run --simulate to generate.")
    else:
        # Banner
        st.info(vc.get("coverage_note", "Coverage measured by Vivado xcrg."))

        # ── Functional Coverage ───────────────────────────────────────────────
        st.markdown("### Functional Coverage")
        st.caption(
            "Source: Vivado 2025.1 xcrg — user-defined covergroups measuring "
            "specification compliance"
        )

        fc_pct = vc.get("functional_coverage_pct", 0.0)
        covergroups = vc.get("covergroups", [])
        fc_d, fc_dc = _fc_delta(fc_pct)

        fc_col1, fc_col2 = st.columns(2)
        fc_col1.metric("Overall Functional Coverage", f"{fc_pct:.1f}%",
                       delta=fc_d, delta_color=fc_dc)
        fc_col2.metric("Covergroups", f"{len(covergroups)} defined")

        if covergroups:
            cg_df = pd.DataFrame([
                {
                    "Covergroup":    _truncate_cg_name(cg["name"]),
                    "VPR Family":    _COVERGROUP_VPR_FAMILY.get(cg["name"], "—"),
                    "Score":         cg["score"],
                    "Bins Covered":  cg.get("covered", 0),
                    "Bins Expected": cg.get("expected", 0),
                }
                for cg in sorted(covergroups, key=lambda c: c["score"])
            ])

            def _color_score_col(series):
                return [
                    "background-color: #0D3320; color: white" if v >= 100
                    else "background-color: #3D3000; color: white" if v >= 80
                    else "background-color: #4A1010; color: white"
                    for v in series
                ]

            styled_cg = (
                cg_df.style
                .format({"Score": "{:.1f}%"})
                .apply(_color_score_col, subset=["Score"])
            )
            st.dataframe(styled_cg, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Code Coverage ─────────────────────────────────────────────────────
        st.markdown("### Code Coverage")
        st.caption(
            "Source: Vivado 2025.1 xcrg — cc_type sbct — structural RTL coverage "
            "measuring implementation completeness"
        )

        line_pct   = vc.get("line_coverage_pct",      0.0)
        branch_pct = vc.get("branch_coverage_pct",    0.0)
        cond_pct   = vc.get("condition_coverage_pct", 0.0)
        toggle_pct = vc.get("toggle_coverage_pct",    0.0)

        cc_col1, cc_col2, cc_col3, cc_col4 = st.columns(4)
        d, dc = _cc_delta(line_pct)
        cc_col1.metric("Line", f"{line_pct:.1f}%", delta=d, delta_color=dc)
        d, dc = _cc_delta(branch_pct)
        cc_col2.metric("Branch", f"{branch_pct:.1f}%", delta=d, delta_color=dc)
        d, dc = _cc_delta(cond_pct)
        cc_col3.metric("Condition", f"{cond_pct:.1f}%", delta=d, delta_color=dc)
        d, dc = _cc_delta(toggle_pct)
        cc_col4.metric("Toggle", f"{toggle_pct:.1f}%", delta=d, delta_color=dc)

        st.caption(
            "Branch coverage gap (26.7%) indicates FIFO boundary conditions and "
            "error paths not yet fully exercised. See CAE gap analysis for details."
        )

        st.markdown("---")

        # ── Weighted Score ────────────────────────────────────────────────────
        st.markdown("### Weighted Verification Score")
        st.caption(
            "Weighted estimate — not a standalone claim. "
            "Formula: (0.7 × Functional + 0.3 × Code Average)"
        )

        wt_score = (0.7 * vc.get("functional_coverage_pct", 0.0) +
                    0.3 * vc.get("code_coverage_pct", 0.0))

        ws_col1, ws_col2, ws_col3 = st.columns(3)
        ws_col1.metric("Functional Weight", "70%")
        ws_col2.metric("Code Weight", "30%")
        ws_col3.metric("Weighted Score", f"{wt_score:.1f}%",
                       help="(0.7 × FC + 0.3 × CC_avg)")

st.markdown("---")


# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown(
    "MIT Licensed | Open Source | "
    "[github.com/BelTechSystems/pssgen](https://github.com/BelTechSystems/pssgen)"
)
st.caption(
    "Generated by pssgen — AI-driven FPGA verification environment generator"
)
