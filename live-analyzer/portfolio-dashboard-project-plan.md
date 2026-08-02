# Personal Investment Portfolio Dashboard — Project Plan & Build Instructions

**Owner:** Bala (single user, personal use only)
**Purpose of this document:** Hand this to the implementing coding agent (Antigravity / Codex) as the full spec. It defines scope, architecture, security rules, and a phased build plan.

---

## 0. Ground Rules for the Implementing Agent

These apply across every phase below, not just once:

1. **No security risks.** This app holds a live brokerage data connection and a full personal net-worth picture. Every design decision defaults to the most private/locked-down option, never the most convenient one.
2. **If anything is ambiguous, stop and ask the owner before proceeding.** Do not silently assume scope, field formats, deployment targets, or security trade-offs. Section 9 lists concrete situations where asking is mandatory.
3. **Open-source tools only**, but the **repository stays private** — this is not being published or open-sourced as a project. No public LICENSE, no public README polish needed, no public deployment.
4. **Zero recurring cost.** Every tool/library/service used must be free for personal use indefinitely, not a free trial.
5. **Read-only against the brokerage.** The app must never call order-placement, modification, or cancellation endpoints — even though the Kite token technically permits it. See Section 7.

---

## 1. Scope

Track total net worth across:
- **Stocks** (via Zerodha holdings)
- **Mutual Funds** (via Zerodha/Coin holdings)
- **Fixed Deposits** (manual entry — no broker API exists for this)
- **Gold** (manual entry — digital gold/SGB/physical)

Single user. Personal device(s) only, via Tailscale. No public internet exposure at all.

---

## 2. Platform Caveats the Agent Must Respect

- **Kite Connect free "Personal" tier** covers holdings, positions, margins, MF holdings, and order/GTT management — but **does not include live or historical market data** (quotes/LTP). That requires the paid Connect plan (₹500/month), which is **out of scope** — do not integrate it.
- **Kite access tokens expire daily.** There is no sandbox and no supported headless re-login. The agent must build a **manual "Reconnect to Kite" button** (OAuth redirect flow) that the owner clicks once each day — not an automated TOTP-based login. Automating 2FA login was explicitly rejected for this project on security grounds.
- **Stock prices**: since Kite's free tier has no quotes, use an open-source NSE data source (e.g. `jugaad-data` or `nsepython`) or `yfinance` as a fallback.
- **MF NAV**: use AMFI's official free daily NAV file (`https://www.amfiindia.com/spages/NAVAll.txt`) — no auth needed, no scraping required.

---

## 3. Architecture

```
[Owner's devices, on Tailscale] ──(tailnet only)──> [App host]
                                                        │
                                          FastAPI backend (Python)
                                          ├─ Kite Connect OAuth + read-only calls
                                          ├─ NSE price lookup (jugaad-data/nsepython)
                                          ├─ AMFI NAV fetch + parse
                                          ├─ Manual asset CRUD (FD, Gold)
                                          ├─ Portfolio valuation + XIRR engine
                                          ├─ Daily snapshot scheduler (APScheduler)
                                          └─ SQLite DB (local file)
                                                        │
                                          React (Vite) frontend, served by the same host
                                          ├─ Overview / net worth cards
                                          ├─ Allocation chart (Recharts)
                                          ├─ Historical trend chart
                                          ├─ Holdings table
                                          ├─ Manual asset forms (FD/Gold)
                                          └─ Reconnect-to-Kite button
```

- **No reverse proxy, no public DNS, no open inbound ports.** The app binds only to the host's Tailscale interface IP.
- **App host**: either the owner's always-on home machine, or a free-tier cloud VM with Tailscale installed and all public ports closed. **Which one to use is an open question — ask the owner (see Section 9).**

---

## 4. Tech Stack (all open source, all free)

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Kite integration | `pykiteconnect` (official Zerodha SDK, free Personal tier) |
| Stock prices | `jugaad-data` or `nsepython` |
| MF NAV | `requests` + plain-text parser against AMFI's free NAV file |
| DB | SQLite via SQLAlchemy (single-user, no need for a DB server) |
| Scheduler | APScheduler (in-process daily job) |
| Frontend | React + Vite, Recharts for charts |
| Network | Tailscale (free personal plan) |
| Secrets | `.env` file, excluded via `.gitignore` |

---

## 5. Data Model

- `manual_assets` — id, asset_type (`FD`/`gold`), fields specific to type (see Section 9 — exact fields need confirmation), created_at
- `holdings_snapshot` — date, asset_type (`stock`/`mf`), symbol_or_scheme, quantity, avg_cost, current_price, current_value
- `portfolio_daily_value` — date, total_value, value_by_asset_class (JSON), for the historical trend chart
- `kite_session` — encrypted access_token, generated_at, expires_at (encrypt at rest — see Section 7)

---

## 6. Security Requirements (explicit checklist)

- App binds **only** to the Tailscale interface IP — never `0.0.0.0` on a publicly routable host.
- All secrets (Kite API key/secret, any app-level password) live in `.env`, never hardcoded, never logged, never committed (`.gitignore` must include `.env` from commit #1).
- GitHub repo is **private**, full stop.
- Kite access token is **encrypted at rest** in the DB (e.g. Fernet symmetric encryption, key from `.env`) — this token can place trades on the real account if it leaks, so it gets the same handling as a password, not just "data."
- App **never calls** `place_order`, `modify_order`, `cancel_order`, or GTT-write endpoints. Only read calls: `get_holdings`, `get_mf_holdings`, `get_positions`, `get_margins`.
- CORS restricted to the frontend's own origin — no wildcard `*`.
- No automated 2FA/TOTP login — manual daily reconnect only (per Section 2).
- Dependencies pinned to specific versions in `requirements.txt` / `package.json`; run `pip audit` / `npm audit` before first deploy and periodically after.
- No portfolio values, holdings, or tokens ever appear in logs, error messages sent to any third-party error-tracking service, or crash reports. If any logging library is used, it must be local-file-only.
- DB backups (if any) stay on the local host or the owner's own storage — never uploaded to third-party cloud storage as part of the build.

---

## 7. Implementation Phases

**Phase 0 — Environment setup**
- Repo scaffold, `.env.example`, `.gitignore`, Python venv, base FastAPI app that returns a health check.
- Confirm Tailscale is installed and the host has a tailnet IP before writing any network-binding code.

**Phase 1 — Kite Connect integration (read-only)**
- Register app on Kite Developer Console, **Personal (free) plan only**.
- Implement OAuth redirect flow: login → request_token → access_token exchange.
- Build the manual "Reconnect" endpoint/button; store token encrypted with expiry.
- Wire up `get_holdings` and `get_mf_holdings` only.

**Phase 2 — Price/NAV enrichment**
- Stock price lookup via `jugaad-data`/`nsepython` for each held symbol.
- AMFI NAV fetch + parse, matched against MF scheme codes from holdings.

**Phase 3 — Manual assets (FD & Gold)**
- CRUD endpoints + simple forms.
- **Exact fields TBD — ask the owner before finalizing the schema (Section 9).**
- Compute current value: FD via interest accrual formula from principal/rate/dates; Gold via grams × current rate (rate entry method also TBD).

**Phase 4 — Portfolio computation engine**
- Per-holding and overall XIRR.
- Asset allocation %, unrealized P&L, category/sector concentration.

**Phase 5 — Daily snapshot + history**
- APScheduler job, once daily, writes a row to `portfolio_daily_value`.
- Powers the net-worth trend chart over time.

**Phase 6 — Backend API surface**
- REST endpoints for: overview, holdings list, manual assets CRUD, trend data, reconnect status.

**Phase 7 — Frontend dashboard**
- Net worth overview, allocation pie chart, trend line chart, holdings table, manual asset forms, Kite reconnect button/status indicator.

**Phase 8 — App-level login (defense in depth)**
- Even though Tailscale already restricts network access to the owner's own devices, add a simple local password gate (hashed, stored via `.env` or DB) as a second layer.

**Phase 9 — Deployment**
- Bind to the Tailscale IP only.
- Run as a long-lived process (systemd service if home server; equivalent on the chosen free VM).
- **Deployment target (home machine vs. free-tier cloud VM) is TBD — ask the owner (Section 9) before this phase starts.**

**Phase 10 — Validation**
- Manual end-to-end test against the real (read-only) Kite holdings — no sandbox exists, so test carefully and confirm no write endpoints are ever exercised, even accidentally.

**Phase 11 — Private documentation**
- A README for the owner's own future reference: Kite app setup, `.env` template, Tailscale setup, how to run/restart the service.

---

## 8. Out of Scope for v1

- Order placement / trading of any kind.
- Multi-user support or sharing access with anyone else.
- A dedicated mobile app (the web dashboard over Tailscale, opened in a phone browser, is sufficient).
- Tax computation / ITR filing.
- The optional multi-model AI "analyze this holding" feature discussed earlier — that's a future add-on, not part of this build.

---

## 9. Mandatory "Ask First" Triggers

The agent must pause and ask the owner directly, rather than assume, whenever:

- Choosing between a **home machine** or a **free-tier cloud VM** for deployment, and (if cloud) which provider.
- Defining the **exact fields** for FD entries (e.g. bank name, principal, rate, compounding frequency, start/maturity date) and Gold entries (form — digital/SGB/physical, purchase date, rate, weight unit).
- Whether **past transaction history** needs to be imported, or the dashboard starts tracking fresh from today's holdings.
- Any step that would require **sudo / system-level changes** on the host.
- Any library or service that turns out to require a **paid tier or a new external account** beyond the Zerodha Kite Developer Console.
- Any point where a design choice would **open a public port** or otherwise widen the network exposure beyond the Tailscale-only model in Section 3.

---

## 10. Deliverables

- Private GitHub repository with the structure above.
- `.env.example` (no real secrets) and a private setup README.
- `requirements.txt` (backend) and `package.json` (frontend), versions pinned.
- A run/start script or systemd unit file for the chosen deployment target.
