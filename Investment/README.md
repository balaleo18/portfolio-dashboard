# Investment Portfolio Analyzer

Local Zerodha/Kite portfolio analysis workspace for tracking holdings, risk, allocation, and action items.

## Current Dashboard

Open the generated dashboard:

```sh
open outputs/kite_dashboard/index.html
```

The current dashboard is generated from a Kite holdings export and includes:

- portfolio value, invested value, and unrealised P&L
- asset allocation and risk buckets
- concentration and risk flags
- top holdings and largest P&L drags
- stress-test scenarios
- target allocation ranges
- cleaned holdings CSV

## Update Workflow

Export holdings from Zerodha/Kite as an `.xlsx` file into `~/Downloads`, then run:

```sh
python3 scripts/update_kite_dashboard.py
```

The script automatically picks the newest `holdings-*.xlsx` file from Downloads.

To force a specific file:

```sh
python3 scripts/update_kite_dashboard.py "/path/to/holdings.xlsx"
```

Outputs are written to:

- `outputs/kite_dashboard/index.html`
- `outputs/kite_dashboard/clean_holdings.csv`

## Next Priorities

- refresh dashboard with the latest Kite data
- add live Kite MCP ingestion so manual XLSX export is optional
- add per-holding value and short-term trade recommendations
- add technical signals: trend, 20/50/200 DMA, drawdown, momentum
- add fundamentals: P/E, P/B, ROE, debt, earnings growth
- store dated snapshots for historical tracking

