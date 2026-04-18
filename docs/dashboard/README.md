# pssgen Verification Dashboard

Streamlit dashboard for the pssgen BALU IP verification status.
Reads live data from GitHub — no local simulation server required.

## Run locally

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

The dashboard opens at http://localhost:8501 and auto-refreshes
data every 5 minutes.

## Deploy to Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Repository: `BelTechSystems/pssgen`
4. Branch: `main`
5. Main file path: `docs/dashboard/dashboard.py`
6. Click **Deploy**

No secrets or environment variables are required — both data
sources are public GitHub raw URLs.

## Data sources

| File | URL |
|------|-----|
| `gap_report.json` | `ip/buffered_axi_lite_uart/gap_report.json` |
| `balu_coverage_results.json` | `ip/buffered_axi_lite_uart/results/balu_coverage_results.json` |

Both files are read from the `main` branch of
`github.com/BelTechSystems/pssgen` on every load (cached 5 minutes).

## Adding a new IP block

When a new IP VPR is added to pssgen:

1. Update `GAP_REPORT_URL` in `dashboard.py` to point to the new
   IP's `gap_report.json`.
2. Update `BALU_COVERAGE_URL` to point to the new IP's
   `balu_coverage_results.json`.
3. Commit and push — Streamlit Cloud redeploys automatically.
