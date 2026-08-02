# Portfolio Dashboard — Consolidation Plan
*Merging "Portfolio Analyzer" (Antigravity) + "Investment" (Codex) into one product*

## 1. What you actually have

These are not two competing builds of the same app — they're two **complementary halves**:

| | Portfolio Analyzer (Antigravity) | Investment (Codex) |
|---|---|---|
| Role | Live infrastructure | Analytics engine |
| Data source | Live Kite OAuth (read-only) + NSE/AMFI fetch | Manual XLSX export from Downloads |
| Storage | SQLite, persisted snapshots | None — regenerates a static HTML file each run |
| Security | Fernet-encrypted token, bcrypt/JWT gate, Tailscale-only | N/A (local script only) |
| Analytics | Valuation, allocation %, XIRR/CAGR | Risk-bucket concentration, 4 stress-test scenarios, target allocation ranges, per-holding trade case (pros/cons/recommendation) |
| Frontend | React + Vite + Recharts (real app shell) | Self-contained static HTML generator |
| Status | Backend routes scaffolded, has been run once (real `.env`/DB in the zip) | 938-line script, 2 git commits, actively used |

Their own roadmaps already point at each other: B's `PROJECT_STATUS.md` lists *"add live Kite MCP ingestion"* and *"add snapshot history"* as next priorities — both of which A already has built. There's no need to pick a winner; **port B's analytics into A's shell.**

## 2. Target architecture (single project)

```
portfolio-dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py, models.py, schemas.py, security.py
│   │   ├── routes/
│   │   │   ├── auth.py, holdings.py, manual.py, portfolio.py
│   │   │   └── analytics.py          ← NEW, ported from Investment
│   │   ├── services/
│   │   │   ├── amfi.py, nse.py, fd.py, gold.py, xirr.py   (from A)
│   │   │   └── risk.py               ← NEW: risk_bucket(), stress_rows(),
│   │   │                                risk_flags(), holding_action() (from B)
│   │   └── scheduler.py              (extend to also snapshot risk metrics)
│   └── requirements.txt               (merged, see §4)
└── frontend/
    └── src/ (React) — add Risk & Stress-Test tab, Recommendations tab
```

**One backend, one DB, one frontend.** B's script becomes a pure-Python module with no I/O side effects (`risk.py`), called from a new `/api/analytics/*` route and rendered as React components instead of a static HTML string.

## 3. Feature reconciliation — what moves where

| Feature (source) | Action |
|---|---|
| `risk_bucket()`, `stress_rows()` (4 scenarios), `risk_flags()` — B | **Port as-is** into `services/risk.py`, operating on A's `HoldingsSnapshot` rows instead of a DataFrame from XLSX |
| `holding_action()` (value case / trade case / pros / cons) — B | Port into `risk.py`; expose via `GET /api/analytics/recommendations` |
| Target allocation ranges — B | Port as config constants; compare against A's live allocation % |
| `find_latest_holdings()`, XLSX parsing (`load_combined`, `find_header_row`) — B | **Keep as a fallback importer only** — useful if Kite OAuth ever lapses and you need to bootstrap from a manual export. Wire it to the same `HoldingsSnapshot` table so it's not a second data path. |
| `bar_svg()`, static HTML template (`build_dashboard`) — B | **Drop.** A's React+Recharts frontend replaces this; no need to maintain two rendering paths. |
| Kite OAuth, encrypted token storage, JWT/bcrypt gate — A | **Keep as the only auth/data path** |
| FD/Gold manual CRUD, XIRR/CAGR — A | **Keep as-is** |
| Daily snapshot scheduler — A | **Extend** to also compute+store risk/stress metrics daily, giving you the historical risk trend B's roadmap wanted, for free |

Net result: you get A's live, secure, scheduled data pipeline **plus** B's more sophisticated risk/recommendation layer, in one app, one DB, no duplicate logic.

## 4. Tech stack decision

Keep A's stack as the base — it's the more complete, better-justified stack (see its own project-plan doc), and B contributes zero infra, only logic:

- **Backend:** FastAPI + SQLAlchemy + SQLite (unchanged)
- **Frontend:** React 19 + Vite + Recharts (unchanged)
- **Analytics:** pandas stays (B's logic is pandas-based) — add it to `backend/requirements.txt`; drop `openpyxl` unless you keep the XLSX fallback importer
- **New backend deps to merge in:** `pandas` (A already has it), keep `openpyxl` only if keeping the fallback importer

Housekeeping before this touches git anywhere:
- Project A's zip contains a live `.env`, `portfolio.db`, and log files — **rotate/regenerate the Fernet key, Kite secret, and app password hash** before merging into a shared repo, and add `portfolio.db`, `*.log`, `.env` to `.gitignore` (A's own security checklist already mandates this — it just wasn't done pre-zip).
- Initialize **one** git repo at the merged root; B's existing 2-commit history can be kept as a subtree/reference in the commit message but doesn't need preserving mechanically.

## 5. Migration steps (phased, in order)

1. **Scaffold**: copy Project A as the new root. Scrub secrets, fix `.gitignore`, re-init git.
2. **Extract B's pure logic**: pull `risk_bucket`, `stress_rows`, `risk_flags`, `holding_action`, `SCENARIOS`, target-allocation constants out of `update_kite_dashboard.py` into `backend/app/services/risk.py`, rewritten against A's `HoldingsSnapshot`/`ManualAsset` models instead of a raw DataFrame.
3. **New route**: `backend/app/routes/analytics.py` exposing stress-test + recommendations + risk flags, reusing A's existing DB session pattern.
4. **Frontend**: add a "Risk & Recommendations" tab reusing existing Recharts setup — table for `holding_action` results, bar chart for stress scenarios (replacing B's hand-rolled `bar_svg`).
5. **Scheduler extension**: after the daily snapshot job in `scheduler.py`, also persist risk-bucket allocation % and flag counts, so risk trend history accumulates automatically (this is literally B's "add snapshot history" roadmap item, solved by reusing A's existing scheduler).
6. **Fallback importer** (optional): keep B's XLSX parsing wired to write into `HoldingsSnapshot` so you can bootstrap/repair data if Kite OAuth is down for a day.
7. **Retire** the old `Investment` repo once analytics.py + frontend tab are verified against a real holdings snapshot; keep the static-HTML script only as a historical reference, not a live path.

## 6. Splitting work between the two agents (for token efficiency)

Rather than handing either agent the whole merged repo, scope each task to the smallest relevant file set — this is the main lever on cost, more than which agent you pick:

| Task | Best-suited agent | Why / what to feed it |
|---|---|---|
| Port `risk.py` logic, rewrite against SQLAlchemy models | Codex (it wrote the original logic, knows its own function contracts) | Feed it only `models.py` + the extracted functions — not A's whole backend |
| New `analytics.py` route + wiring into `main.py` | Either — this is thin glue code | Feed only `main.py`, `database.py`, and the new `risk.py` |
| React "Risk & Recommendations" tab | Antigravity (already owns the frontend patterns/components) | Feed only `App.jsx` + one existing route file as a style reference, not the whole `src/` |
| Scheduler extension for risk history | Antigravity (owns `scheduler.py` already) | Feed only `scheduler.py` + `models.py` |
| Secret rotation / `.gitignore` / repo scaffolding | Either, low-stakes — do this manually or with a cheap/small model, not a full agent run | — |

General rules to keep token cost down across both agents going forward:
- **One shared spec, not two.** Merge `portfolio-dashboard-project-plan.md` (A) and `PROJECT_STATUS.md` (B) into a single living `PROJECT_STATUS.md` at the new root; update it after each task instead of re-deriving context each session.
- **Task-scoped context, not whole-repo context.** Point each agent at the specific module directory (`backend/app/services/`, or `frontend/src/`) rather than the project root, especially since `node_modules/` and `venv/` are sitting inside the zip — exclude those from any context entirely.
- **Checklist-driven handoff.** Use the phased list in §5 as literal tickets; check one off per session so neither agent re-reads finished work to "figure out where things stand."
