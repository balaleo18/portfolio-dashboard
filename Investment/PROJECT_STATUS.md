# Project Status

## Completed

- `scripts/update_kite_dashboard.py` parses Zerodha/Kite holdings exports.
- `outputs/kite_dashboard/index.html` renders a local static dashboard.
- `outputs/kite_dashboard/clean_holdings.csv` stores the cleaned holdings table.
- Dashboard currently includes allocation, risk buckets, top holdings, drags, stress tests, risk flags, and target allocation guidance.
- The initial project baseline has been committed to git.
- Dashboard now includes per-holding value case, short-term trade case, pros, cons, and recommendation.

## Pending

- Refresh the dashboard from the latest available holdings.
- Add live Kite MCP ingestion.
- Add technical and fundamental data enrichment.
- Add snapshot history for tracking changes over time.

## Recommended Course

1. Stabilize and commit the current export-based dashboard.
2. Add live Kite MCP data capture as a separate ingestion path.
3. Generate dated snapshots under `outputs/snapshots/`.
4. Add recommendation columns and risk labels directly to the dashboard.
5. Add market-data enrichment after the portfolio pipeline is repeatable.

