# pssgen Grafana Dashboard

## Grafana Cloud setup (recommended)

1. In your Grafana Cloud instance, install the Infinity datasource plugin
2. Add a datasource named "pssgen-gap-report" (type: Infinity, no base URL)
3. Import `docs/grafana/dashboards/pssgen_verification.json` via
   Dashboards → Import
4. The dashboard reads live data from:
   https://raw.githubusercontent.com/BelTechSystems/pssgen/main/ip/buffered_axi_lite_uart/gap_report.json
5. Data updates automatically on every `pssgen --collect-results` + git push

## Local Docker setup (optional)

Requires Docker Desktop.

```
cd docs/grafana
docker compose up -d
```

Open http://localhost:3000 (admin / pssgen)

## Updating the dashboard

After running `pssgen --collect-results`, git push updates the
raw GitHub URL. Grafana refreshes automatically every 5 minutes
or on manual refresh.
