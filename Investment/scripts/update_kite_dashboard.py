#!/usr/bin/env python3
"""
Generate a local HTML dashboard from a Zerodha Kite holdings export.

Usage:
  python3 scripts/update_kite_dashboard.py
  python3 scripts/update_kite_dashboard.py "/path/to/holdings.xlsx"
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = WORKSPACE / "outputs" / "kite_dashboard"
DOWNLOADS = Path.home() / "Downloads"


@dataclass(frozen=True)
class Scenario:
    name: str
    shocks: dict[str, float]


SCENARIOS = [
    Scenario(
        "10% India equity correction",
        {
            "Core/direct equity": -0.10,
            "High beta / small-mid-factor": -0.14,
            "Mid/broad equity": -0.12,
            "Global equity FoF": -0.05,
            "Low-vol hybrid/arbitrage": -0.005,
            "Hybrid/other FoF": -0.01,
            "Debt / liquidity": 0.0,
        },
    ),
    Scenario(
        "15% India equity correction",
        {
            "Core/direct equity": -0.15,
            "High beta / small-mid-factor": -0.22,
            "Mid/broad equity": -0.18,
            "Global equity FoF": -0.08,
            "Low-vol hybrid/arbitrage": -0.01,
            "Hybrid/other FoF": -0.015,
            "Debt / liquidity": -0.0025,
        },
    ),
    Scenario(
        "Small/mid/factor -30%",
        {
            "Core/direct equity": -0.06,
            "High beta / small-mid-factor": -0.30,
            "Mid/broad equity": -0.22,
            "Global equity FoF": -0.05,
            "Low-vol hybrid/arbitrage": 0.0,
            "Hybrid/other FoF": -0.01,
            "Debt / liquidity": 0.0,
        },
    ),
    Scenario(
        "Oil + INR risk-off shock",
        {
            "Core/direct equity": -0.12,
            "High beta / small-mid-factor": -0.20,
            "Mid/broad equity": -0.16,
            "Global equity FoF": 0.05,
            "Low-vol hybrid/arbitrage": -0.005,
            "Hybrid/other FoF": -0.005,
            "Debt / liquidity": -0.005,
        },
    ),
    Scenario("Credit event in weak listed debt", {"Debt / liquidity": -0.085}),
]


def find_latest_holdings() -> Path:
    candidates = sorted(
        DOWNLOADS.glob("holdings-*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No holdings-*.xlsx file found in {DOWNLOADS}. Pass a file path explicitly."
        )
    return candidates[0]


def clean_label(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_statement_date(raw: pd.DataFrame) -> str:
    pattern = re.compile(r"as on\s+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
    for value in raw.astype(str).to_numpy().ravel():
        match = pattern.search(value)
        if match:
            return match.group(1)
    return "Unknown"


def find_header_row(raw: pd.DataFrame) -> int:
    for idx, row in raw.iterrows():
        labels = {clean_label(v).lower() for v in row.tolist()}
        if "symbol" in labels and "isin" in labels:
            return int(idx)
    raise ValueError("Could not find a holdings table header row with Symbol and ISIN.")


def load_combined(path: Path) -> tuple[pd.DataFrame, str]:
    xls = pd.ExcelFile(path)
    sheet = "Combined" if "Combined" in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    statement_date = parse_statement_date(raw)
    header_idx = find_header_row(raw)
    df = raw.iloc[header_idx + 1 :].copy()
    df.columns = [clean_label(c) for c in raw.iloc[header_idx].tolist()]
    df = df.dropna(how="all")
    df = df.loc[:, [c for c in df.columns if c]]
    df = df.rename(columns={"Unrealize P&L Pct.": "Unrealized P&L Pct."})

    required = [
        "Symbol",
        "Sector",
        "Instrument Type",
        "Quantity Available",
        "Average Price",
        "Previous Closing Price",
        "Unrealized P&L",
        "Unrealized P&L Pct.",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected column(s): {', '.join(missing)}")

    for col in [
        "Quantity Available",
        "Quantity Discrepant",
        "Quantity Long Term",
        "Quantity Pledged (Margin)",
        "Quantity Pledged (Loan)",
        "Average Price",
        "Previous Closing Price",
        "Unrealized P&L",
        "Unrealized P&L Pct.",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in ["Symbol", "Sector", "Instrument Type", "ISIN"]:
        if col in df.columns:
            df[col] = df[col].fillna("-").astype(str).str.strip()

    df["Invested Value"] = df["Quantity Available"] * df["Average Price"]
    df["Present Value"] = df["Quantity Available"] * df["Previous Closing Price"]
    df = df[df["Present Value"] > 0].copy()
    total = df["Present Value"].sum()
    df["Weight %"] = df["Present Value"] / total * 100 if total else 0
    df["Asset Class"] = df.apply(asset_class, axis=1)
    df["Risk Bucket"] = df.apply(risk_bucket, axis=1)
    return df, statement_date


def asset_class(row: pd.Series) -> str:
    instrument = str(row.get("Instrument Type", "-"))
    sector = str(row.get("Sector", "-"))
    if instrument and instrument != "-":
        if instrument.startswith("Debt"):
            return "MF debt/liquid"
        if instrument.startswith("Hybrid"):
            return "MF hybrid/arbitrage"
        if instrument.startswith("Equity"):
            return "MF active equity"
        if "Index Funds/ETFs" in instrument:
            return "MF index/factor"
        if "Fund of Funds" in instrument:
            return "MF FoF/global/other"
        return "MF other"
    if sector == "DEBT":
        return "Direct listed debt"
    if sector == "ETF":
        return "Listed ETF/commodity"
    return "Direct equity"


def risk_bucket(row: pd.Series) -> str:
    asset = row["Asset Class"] if "Asset Class" in row else asset_class(row)
    instrument = str(row.get("Instrument Type", "-"))
    sector = str(row.get("Sector", "-"))
    symbol = str(row.get("Symbol", "")).upper()

    if asset in {"MF debt/liquid", "Direct listed debt"}:
        return "Debt / liquidity"
    if asset == "MF hybrid/arbitrage":
        return "Low-vol hybrid/arbitrage"
    if asset == "MF FoF/global/other":
        if any(token in symbol for token in ["U.S.", "US ", "CHINA", "GLOBAL"]):
            return "Global equity FoF"
        return "Hybrid/other FoF"
    if (
        "Small Cap" in instrument
        or "MICROCAP" in symbol
        or sector in {"REAL ESTATE", "DEFENCE"}
        or any(token in symbol for token in ["SMALL", "ALPHA", "MOMENTUM"])
    ):
        return "High beta / small-mid-factor"
    if "Mid Cap" in instrument or "NEXT 50" in symbol or "NIFTY500" in symbol:
        return "Mid/broad equity"
    return "Core/direct equity"


def fmt_inr(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(float(value))
    if value >= 10_000_000:
        return f"{sign}Rs. {value / 10_000_000:.2f} Cr"
    return f"{sign}Rs. {value / 100_000:.2f} L"


def fmt_pct(value: float) -> str:
    return f"{float(value):.1f}%"


def records_for_group(df: pd.DataFrame, group_col: str, limit: int | None = None) -> list[dict[str, Any]]:
    grouped = (
        df.groupby(group_col, dropna=False)
        .agg(
            value=("Present Value", "sum"),
            pnl=("Unrealized P&L", "sum"),
            count=("Symbol", "count"),
        )
        .sort_values("value", ascending=False)
        .reset_index()
    )
    total = df["Present Value"].sum()
    grouped["weight"] = grouped["value"] / total * 100 if total else 0
    if limit:
        grouped = grouped.head(limit)
    return grouped.to_dict(orient="records")


def stress_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    total = float(df["Present Value"].sum())
    bucket_values = df.groupby("Risk Bucket")["Present Value"].sum().to_dict()
    rows = []
    for scenario in SCENARIOS:
        loss = sum(bucket_values.get(bucket, 0.0) * shock for bucket, shock in scenario.shocks.items())
        rows.append(
            {
                "scenario": scenario.name,
                "loss": loss,
                "loss_pct": loss / total * 100 if total else 0,
                "ending": total + loss,
            }
        )
    return rows


def risk_flags(df: pd.DataFrame) -> list[dict[str, str]]:
    total = df["Present Value"].sum()
    flags: list[dict[str, str]] = []

    top = df.sort_values("Present Value", ascending=False).iloc[0]
    if top["Weight %"] > 15:
        flags.append(
            {
                "severity": "High",
                "title": "Single holding concentration",
                "detail": f"{top['Symbol']} is {top['Weight %']:.1f}% of the Kite sleeve. This is opportunity-cost concentration even if the fund is low volatility.",
            }
        )

    weak_debt = df[
        (df["Asset Class"].eq("Direct listed debt"))
        & (df["Unrealized P&L Pct."] <= -20)
    ].sort_values("Unrealized P&L Pct.")
    if not weak_debt.empty:
        row = weak_debt.iloc[0]
        flags.append(
            {
                "severity": "High",
                "title": "Credit/liquidity risk in listed debt",
                "detail": f"{row['Symbol']} is down {row['Unrealized P&L Pct.']:.1f}% and still worth {fmt_inr(row['Present Value'])}. Treat this as a credit review item, not a normal bond fluctuation.",
            }
        )

    direct = df[df["Instrument Type"].eq("-")]
    financial_weight = direct.loc[direct["Sector"].eq("FINANCIAL SERVICES"), "Present Value"].sum()
    if financial_weight / total > 0.10:
        flags.append(
            {
                "severity": "Medium",
                "title": "Financial services and market-infrastructure overlap",
                "detail": f"Financial services is {financial_weight / total * 100:.1f}% of the total sleeve and includes several correlated capital-market platform names.",
            }
        )

    tiny_count = int((df["Weight %"] < 0.5).sum())
    if tiny_count >= 20:
        flags.append(
            {
                "severity": "Medium",
                "title": "Too many immaterial positions",
                "detail": f"{tiny_count} holdings are below 0.5% weight. They add monitoring load without meaningful return impact.",
            }
        )

    defensive = df[df["Risk Bucket"].isin(["Low-vol hybrid/arbitrage", "Debt / liquidity"])]
    defensive_weight = defensive["Present Value"].sum() / total * 100 if total else 0
    if defensive_weight > 40:
        flags.append(
            {
                "severity": "Medium",
                "title": "Under-risked for aggressive growth",
                "detail": f"Debt, liquid, and arbitrage-like exposure is {defensive_weight:.1f}%. Good dry powder, but high opportunity cost over 3-5 years.",
            }
        )

    return flags


def bar_svg(rows: list[dict[str, Any]], label_key: str, value_key: str = "weight", max_rows: int = 10) -> str:
    rows = rows[:max_rows]
    max_value = max([float(r[value_key]) for r in rows] + [1])
    parts = []
    for row in rows:
        label = html.escape(str(row[label_key]))
        value = float(row[value_key])
        width = max(2, value / max_value * 100)
        parts.append(
            f"""
            <div class="bar-row">
              <div class="bar-label" title="{label}">{label}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>
              <div class="bar-value">{fmt_pct(value)}</div>
            </div>
            """
        )
    return "\n".join(parts)


def table_html(headers: list[str], rows: list[list[Any]], classes: str = "") -> str:
    thead = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return f"<table class=\"{classes}\"><thead><tr>{thead}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def cell(value: Any) -> str:
    return html.escape(str(value))


def signed_class(value: float) -> str:
    if value > 0:
        return "pos"
    if value < 0:
        return "neg"
    return ""


def holding_action(row: pd.Series) -> dict[str, str]:
    symbol = str(row["Symbol"])
    sector = str(row["Sector"])
    asset = str(row["Asset Class"])
    risk = str(row["Risk Bucket"])
    pnl_pct = float(row["Unrealized P&L Pct."])
    weight = float(row["Weight %"])

    is_fund = asset.startswith("MF")
    is_debt = risk == "Debt / liquidity"
    is_high_beta = risk == "High beta / small-mid-factor"
    is_direct_equity = asset == "Direct equity"

    if is_debt and pnl_pct <= -20:
        rec = "Exit/Review"
        value_case = "Credit/liquidity risk dominates valuation; do not average before issuer-level review."
        trade_case = "No short-term trade case; treat as recovery/exit decision."
    elif is_direct_equity and pnl_pct <= -20:
        rec = "Exit/Review"
        value_case = "Deep drawdown; thesis needs fresh fundamentals before adding."
        trade_case = "Momentum is broken; wait for base formation or reclaim of trend."
    elif weight > 10 and risk in {"Low-vol hybrid/arbitrage", "Debt / liquidity"}:
        rec = "Trim"
        value_case = "Useful defensive asset, but position size creates opportunity cost."
        trade_case = "No urgency; reduce gradually into liquidity or redeploy on equity corrections."
    elif pnl_pct >= 25 and (is_direct_equity or is_high_beta):
        rec = "Trim"
        value_case = "Good winner; protect capital if valuation has run ahead of earnings."
        trade_case = "Trail profits; book partial gains on failed breakout or high-volume reversal."
    elif is_fund and risk in {"Core/direct equity", "Mid/broad equity"}:
        rec = "Buy/Add"
        value_case = "Cleaner diversified compounding sleeve."
        trade_case = "Add on market pullbacks instead of chasing sharp rallies."
    elif is_direct_equity and pnl_pct >= -10:
        rec = "Hold"
        value_case = "Maintain while thesis and earnings quality remain intact."
        trade_case = "Hold; add only after strength confirms or support retest holds."
    elif is_high_beta:
        rec = "Hold"
        value_case = "High-beta exposure can compound, but valuation risk is higher."
        trade_case = "Size carefully; avoid averaging during momentum fades."
    else:
        rec = "Hold"
        value_case = "Position is acceptable but not a priority add."
        trade_case = "Monitor; wait for a clear trend or valuation trigger."

    pros = "Diversifies the sleeve." if is_fund else f"Adds exposure to {sector.lower()}."
    if pnl_pct > 0:
        pros += " Position is currently profitable."
    if risk in {"Low-vol hybrid/arbitrage", "Debt / liquidity"}:
        pros += " Provides defensive ballast."

    cons = "Limited direct alpha impact at small weight." if weight < 0.5 else "Needs active monitoring."
    if pnl_pct < -10:
        cons += " Current drawdown is a warning signal."
    if is_high_beta:
        cons += " High-beta sleeve can reverse quickly."
    if is_debt and pnl_pct <= -20:
        cons += " Possible value trap or credit event."

    return {
        "recommendation": rec,
        "value_case": value_case,
        "trade_case": trade_case,
        "pros": pros,
        "cons": cons,
    }


def build_dashboard(df: pd.DataFrame, input_path: Path, statement_date: str) -> str:
    total = float(df["Present Value"].sum())
    invested = float(df["Invested Value"].sum())
    pnl = float(df["Unrealized P&L"].sum())
    pnl_pct = pnl / invested * 100 if invested else 0
    top5 = float(df.nlargest(5, "Present Value")["Weight %"].sum())
    top10 = float(df.nlargest(10, "Present Value")["Weight %"].sum())
    defensive_weight = (
        df[df["Risk Bucket"].isin(["Low-vol hybrid/arbitrage", "Debt / liquidity"])]["Present Value"].sum()
        / total
        * 100
    )
    equity_growth_weight = 100 - defensive_weight

    asset_rows = records_for_group(df, "Asset Class")
    risk_rows = records_for_group(df, "Risk Bucket")
    sector_rows = records_for_group(df, "Sector", 12)
    top_rows = df.sort_values("Present Value", ascending=False).head(20)
    worst_rows = df.sort_values("Unrealized P&L").head(12)
    action_rows = df.assign(**df.apply(lambda row: pd.Series(holding_action(row)), axis=1))
    stress = stress_rows(df)
    flags = risk_flags(df)

    target_rows = [
        ["Core India equity", "35-45%", "Build through Nifty 50/100, quality/flexi-cap, and strongest direct holdings."],
        ["Mid/small/factor equity", "15-20%", "Add slowly; use corrections because smallcap valuations are vulnerable."],
        ["Direct high-conviction stocks", "15-20%", "Consolidate tiny positions into names you can size at 1.5-3%."],
        ["Global equity", "8-12%", "Increase to hedge INR depreciation and India-specific shocks."],
        ["Debt/liquid/arbitrage", "15-25%", "Keep dry powder, but reduce excess arbitrage concentration."],
        ["Gold/silver/commodity hedge", "3-6%", "Maintain as macro and currency hedge."],
    ]

    top_table = table_html(
        ["Holding", "Bucket", "Value", "Weight", "P&L"],
        [
            [
                cell(row["Symbol"]),
                cell(row["Asset Class"]),
                cell(fmt_inr(row["Present Value"])),
                cell(fmt_pct(row["Weight %"])),
                f"<span class=\"{signed_class(row['Unrealized P&L'])}\">{cell(fmt_inr(row['Unrealized P&L']))} ({cell(fmt_pct(row['Unrealized P&L Pct.']))})</span>",
            ]
            for _, row in top_rows.iterrows()
        ],
        "dense",
    )

    worst_table = table_html(
        ["Holding", "Sector", "Value", "Weight", "P&L"],
        [
            [
                cell(row["Symbol"]),
                cell(row["Sector"]),
                cell(fmt_inr(row["Present Value"])),
                cell(fmt_pct(row["Weight %"])),
                f"<span class=\"{signed_class(row['Unrealized P&L'])}\">{cell(fmt_inr(row['Unrealized P&L']))} ({cell(fmt_pct(row['Unrealized P&L Pct.']))})</span>",
            ]
            for _, row in worst_rows.iterrows()
        ],
        "dense",
    )

    asset_table = table_html(
        ["Bucket", "Value", "Weight", "P&L", "Count"],
        [
            [
                cell(row["Asset Class"]),
                cell(fmt_inr(row["value"])),
                cell(fmt_pct(row["weight"])),
                f"<span class=\"{signed_class(row['pnl'])}\">{cell(fmt_inr(row['pnl']))}</span>",
                cell(int(row["count"])),
            ]
            for row in asset_rows
        ],
        "dense",
    )

    stress_table = table_html(
        ["Scenario", "Impact", "Impact %", "Ending Value"],
        [
            [
                cell(row["scenario"]),
                f"<span class=\"{signed_class(row['loss'])}\">{cell(fmt_inr(row['loss']))}</span>",
                f"<span class=\"{signed_class(row['loss_pct'])}\">{cell(fmt_pct(row['loss_pct']))}</span>",
                cell(fmt_inr(row["ending"])),
            ]
            for row in stress
        ],
        "dense",
    )

    target_table = table_html(["Sleeve", "Target", "Action"], [[cell(c) for c in row] for row in target_rows], "dense")

    actions_table = table_html(
        ["Holding", "Weight", "P&L", "Recommendation", "Value Case", "Trade Case", "Pros", "Cons"],
        [
            [
                cell(row["Symbol"]),
                cell(fmt_pct(row["Weight %"])),
                f"<span class=\"{signed_class(row['Unrealized P&L'])}\">{cell(fmt_inr(row['Unrealized P&L']))} ({cell(fmt_pct(row['Unrealized P&L Pct.']))})</span>",
                cell(row["recommendation"]),
                cell(row["value_case"]),
                cell(row["trade_case"]),
                cell(row["pros"]),
                cell(row["cons"]),
            ]
            for _, row in action_rows.sort_values(["recommendation", "Weight %"], ascending=[True, False]).iterrows()
        ],
        "dense",
    )

    action_counts = action_rows["recommendation"].value_counts().to_dict()
    action_summary = ", ".join(
        f"{html.escape(str(key))}: {int(value)}"
        for key, value in sorted(action_counts.items())
    )

    flag_cards = "\n".join(
        f"""
        <article class="flag {html.escape(flag['severity']).lower()}">
          <div class="severity">{html.escape(flag['severity'])}</div>
          <h3>{html.escape(flag['title'])}</h3>
          <p>{html.escape(flag['detail'])}</p>
        </article>
        """
        for flag in flags
    )

    command = (
        f"{html.escape(str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'))} "
        f"{html.escape(str(WORKSPACE / 'scripts' / 'update_kite_dashboard.py'))} "
        f"&quot;{html.escape(str(input_path))}&quot;"
    )
    auto_command = (
        f"{html.escape(str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'))} "
        f"{html.escape(str(WORKSPACE / 'scripts' / 'update_kite_dashboard.py'))}"
    )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_blob = json.dumps(
        {
            "source": str(input_path),
            "statement_date": statement_date,
            "generated_at": generated,
            "total_present_value": total,
            "invested_value": invested,
            "unrealized_pnl": pnl,
            "asset_allocation": asset_rows,
            "risk_buckets": risk_rows,
            "sector_exposure": sector_rows,
            "stress_tests": stress,
            "risk_flags": flags,
            "recommendations": action_counts,
        },
        indent=2,
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kite Portfolio Dashboard</title>
  <style>
    :root {{
      --bg: #f5f7f9;
      --panel: #ffffff;
      --ink: #16202a;
      --muted: #64707d;
      --line: #dde4eb;
      --blue: #1e5b9a;
      --teal: #167c75;
      --green: #147a3f;
      --red: #b42318;
      --amber: #a15c00;
      --shadow: 0 12px 30px rgba(22, 32, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      background: #102235;
      color: white;
      padding: 28px 32px;
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    header p {{
      margin: 0;
      color: #c9d5e2;
      font-size: 14px;
    }}
    main {{
      padding: 24px 32px 40px;
      max-width: 1480px;
      margin: 0 auto;
    }}
    .grid {{
      display: grid;
      gap: 16px;
    }}
    .kpis {{
      grid-template-columns: repeat(6, minmax(150px, 1fr));
      margin-top: -44px;
    }}
    .two {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
    .three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .kpi .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .06em;
      margin-bottom: 8px;
    }}
    .kpi .value {{
      font-size: 24px;
      font-weight: 750;
      white-space: nowrap;
    }}
    .kpi .note {{
      margin-top: 6px;
      font-size: 12px;
      color: var(--muted);
    }}
    h2 {{
      font-size: 18px;
      margin: 0 0 14px;
      letter-spacing: 0;
    }}
    h3 {{
      font-size: 15px;
      margin: 0 0 8px;
    }}
    p, li {{
      color: var(--muted);
      line-height: 1.5;
    }}
    .section {{ margin-top: 18px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th {{
      text-align: left;
      color: var(--muted);
      font-weight: 700;
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      white-space: nowrap;
    }}
    td {{
      border-bottom: 1px solid #edf1f5;
      padding: 9px 8px;
      vertical-align: top;
    }}
    .dense td, .dense th {{ font-size: 12.5px; }}
    .pos {{ color: var(--green); font-weight: 650; }}
    .neg {{ color: var(--red); font-weight: 650; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(120px, 220px) minmax(120px, 1fr) 56px;
      gap: 12px;
      align-items: center;
      margin: 10px 0;
      font-size: 13px;
    }}
    .bar-label {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--ink);
      font-weight: 600;
    }}
    .bar-track {{
      height: 10px;
      background: #e8eef4;
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--blue), var(--teal));
      border-radius: 999px;
    }}
    .bar-value {{
      text-align: right;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}
    .flag {{
      border: 1px solid var(--line);
      border-left: 4px solid var(--amber);
      border-radius: 8px;
      padding: 14px;
      background: #fff;
    }}
    .flag.high {{ border-left-color: var(--red); }}
    .severity {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--muted);
      font-weight: 800;
      margin-bottom: 8px;
    }}
    .flag p {{ margin: 0; font-size: 13px; }}
    .diagnosis {{
      border-left: 4px solid var(--blue);
    }}
    code, pre {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    pre {{
      overflow-x: auto;
      background: #101820;
      color: #e6edf3;
      padding: 14px;
      border-radius: 8px;
      font-size: 12px;
      line-height: 1.45;
    }}
    details {{
      margin-top: 12px;
    }}
    summary {{
      cursor: pointer;
      color: var(--blue);
      font-weight: 700;
    }}
    @media (max-width: 1100px) {{
      .kpis {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .two, .three {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 700px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      .kpis {{ grid-template-columns: 1fr 1fr; }}
      .kpi .value {{ font-size: 19px; }}
      .bar-row {{ grid-template-columns: 1fr 54px; }}
      .bar-track {{ grid-column: 1 / -1; grid-row: 2; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Kite Portfolio Dashboard</h1>
    <p>Source: {html.escape(str(input_path))} | Statement date: {html.escape(statement_date)} | Generated: {html.escape(generated)}</p>
  </header>
  <main>
    <section class="grid kpis">
      <div class="card kpi"><div class="label">Present value</div><div class="value">{fmt_inr(total)}</div><div class="note">Kite sleeve only</div></div>
      <div class="card kpi"><div class="label">Invested value</div><div class="value">{fmt_inr(invested)}</div><div class="note">Computed from quantity x average</div></div>
      <div class="card kpi"><div class="label">Unrealized P&L</div><div class="value {signed_class(pnl)}">{fmt_inr(pnl)}</div><div class="note">{fmt_pct(pnl_pct)}</div></div>
      <div class="card kpi"><div class="label">Holdings</div><div class="value">{len(df)}</div><div class="note">Combined sheet rows</div></div>
      <div class="card kpi"><div class="label">Top 10 weight</div><div class="value">{fmt_pct(top10)}</div><div class="note">Top 5: {fmt_pct(top5)}</div></div>
      <div class="card kpi"><div class="label">Growth exposure</div><div class="value">{fmt_pct(equity_growth_weight)}</div><div class="note">Rest is debt/liquid/arbitrage</div></div>
    </section>

    <section class="grid two section">
      <div class="card diagnosis">
        <h2>Professional Diagnosis</h2>
        <p>This Kite sleeve is more defensive than an aggressive 3-5 year portfolio. Debt, liquid, and arbitrage-like exposure is {fmt_pct(defensive_weight)}, while true growth exposure is about {fmt_pct(equity_growth_weight)}. That protects drawdowns, but creates opportunity cost if Indian earnings and liquidity improve.</p>
        <p>The main action is not to add more random stocks. It is to reduce excess arbitrage concentration, keep enough dry powder, consolidate tiny positions, and increase cleaner core equity plus global diversification.</p>
      </div>
      <div class="card">
        <h2>Update Command</h2>
        <p>Run this after downloading a new Kite holdings export. With no file path, it automatically picks the newest <code>holdings-*.xlsx</code> from Downloads.</p>
        <pre>{auto_command}</pre>
        <p>To force a specific file:</p>
        <pre>{command}</pre>
      </div>
    </section>

    <section class="grid two section">
      <div class="card">
        <h2>Asset Allocation</h2>
        {bar_svg(asset_rows, "Asset Class")}
      </div>
      <div class="card">
        <h2>Risk Buckets</h2>
        {bar_svg(risk_rows, "Risk Bucket")}
      </div>
    </section>

    <section class="grid two section">
      <div class="card">
        <h2>Risk Flags</h2>
        <div class="grid">
          {flag_cards}
        </div>
      </div>
      <div class="card">
        <h2>Stress Tests</h2>
        {stress_table}
      </div>
    </section>

    <section class="grid two section">
      <div class="card">
        <h2>Allocation Detail</h2>
        {asset_table}
      </div>
      <div class="card">
        <h2>Sector Exposure</h2>
        {bar_svg(sector_rows, "Sector")}
      </div>
    </section>

    <section class="card section">
      <h2>Top Holdings</h2>
      {top_table}
    </section>

    <section class="card section">
      <h2>Largest P&L Drags</h2>
      {worst_table}
    </section>

    <section class="card section">
      <h2>Suggested Target Ranges</h2>
      {target_table}
    </section>

    <section class="card section">
      <h2>Holdings Analysis</h2>
      <p>Recommendation count: {action_summary}. Every row includes a value case and short-term trade case.</p>
      {actions_table}
    </section>

    <section class="card section">
      <h2>Machine-Readable Snapshot</h2>
      <p>This embedded data lets the dashboard be audited or reused later.</p>
      <details>
        <summary>Show JSON snapshot</summary>
        <pre>{html.escape(data_blob)}</pre>
      </details>
    </section>
  </main>
</body>
</html>
"""


def write_outputs(df: pd.DataFrame, input_path: Path, statement_date: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_text = build_dashboard(df, input_path, statement_date)
    index_path = output_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")

    csv_path = output_dir / "clean_holdings.csv"
    df.sort_values("Present Value", ascending=False).to_csv(csv_path, index=False)
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Kite portfolio dashboard.")
    parser.add_argument("xlsx", nargs="?", help="Path to Kite holdings .xlsx export.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    args = parser.parse_args()

    input_path = Path(args.xlsx).expanduser() if args.xlsx else find_latest_holdings()
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    df, statement_date = load_combined(input_path)
    output = write_outputs(df, input_path, statement_date, Path(args.output_dir).expanduser().resolve())
    print(f"Dashboard updated: {output}")
    print(f"Holdings parsed: {len(df)}")
    print(f"Present value: {fmt_inr(float(df['Present Value'].sum()))}")


if __name__ == "__main__":
    main()
