import logging
from sqlalchemy.orm import Session
from backend.app.models import HoldingsSnapshot, ManualAsset

logger = logging.getLogger(__name__)

class Scenario:
    def __init__(self, name: str, shocks: dict[str, float]):
        self.name = name
        self.shocks = shocks

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

def asset_class(instrument: str, sector: str) -> str:
    instrument = str(instrument or "-").strip()
    sector = str(sector or "-").strip().upper()
    
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

def risk_bucket(asset: str, instrument: str, sector: str, symbol: str) -> str:
    asset = str(asset or "")
    instrument = str(instrument or "-").strip()
    sector = str(sector or "-").strip().upper()
    symbol = str(symbol or "").upper()

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

def holding_action(symbol: str, sector: str, asset: str, risk: str, pnl_pct: float, weight: float) -> dict[str, str]:
    symbol = str(symbol or "")
    sector = str(sector or "")
    asset = str(asset or "")
    risk = str(risk or "")
    pnl_pct = float(pnl_pct or 0.0)
    weight = float(weight or 0.0)

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

def resolve_sector_and_type(db: Session, symbol_or_scheme: str, asset_type: str) -> tuple[str, str]:
    """
    Looks up the latest snapshot in the database to retrieve the Sector and Instrument Type
    for a given holding. If not found, defaults to '-'.
    """
    latest = db.query(HoldingsSnapshot).filter(
        HoldingsSnapshot.symbol_or_scheme == symbol_or_scheme,
        HoldingsSnapshot.sector != "-",
        HoldingsSnapshot.sector != None
    ).order_by(HoldingsSnapshot.date.desc()).first()
    
    if latest:
        return latest.sector or "-", latest.instrument_type or "-"
        
    return "-", "-"

def calculate_risk_metrics(db: Session, holdings_data: dict) -> dict:
    """
    Calculates asset class allocation, risk bucket allocation, sector exposure,
    stress test shocks, and warning flags for the active portfolio holdings.
    """
    stocks = holdings_data.get("stocks", [])
    mfs = holdings_data.get("mutual_funds", [])
    fds = holdings_data.get("fixed_deposits", [])
    gold = holdings_data.get("gold", [])
    
    # 1. Compile processed list of holdings
    processed_holdings = []
    
    for s in stocks:
        symbol = s["symbol"]
        qty = s["quantity"]
        avg_cost = s["average_price"]
        curr_price = s["current_price"]
        current_value = s["current_value"]
        pnl = s["pnl"]
        pnl_pct = s["pnl_percentage"]
        
        sector, inst_type = resolve_sector_and_type(db, symbol, "stock")
        ac = asset_class(inst_type, sector)
        rb = risk_bucket(ac, inst_type, sector, symbol)
        
        processed_holdings.append({
          "symbol": symbol,
          "name": s.get("name", symbol),
          "asset_type": "stock",
          "quantity": qty,
          "avg_cost": avg_cost,
          "current_price": curr_price,
          "current_value": current_value,
          "pnl": pnl,
          "pnl_percentage": pnl_pct,
          "sector": sector,
          "instrument_type": inst_type,
          "asset_class": ac,
          "risk_bucket": rb
        })
        
    for m in mfs:
        isin = m["isin"]
        qty = m["quantity"]
        avg_cost = m["average_price"]
        curr_price = m["current_price"]
        current_value = m["current_value"]
        pnl = m["pnl"]
        pnl_pct = m["pnl_percentage"]
        
        sector, inst_type = resolve_sector_and_type(db, isin, "mf")
        ac = asset_class(inst_type, sector)
        rb = risk_bucket(ac, inst_type, sector, isin)
        
        processed_holdings.append({
          "symbol": isin,
          "name": m.get("name", isin),
          "asset_type": "mf",
          "quantity": qty,
          "avg_cost": avg_cost,
          "current_price": curr_price,
          "current_value": current_value,
          "pnl": pnl,
          "pnl_percentage": pnl_pct,
          "sector": sector,
          "instrument_type": inst_type,
          "asset_class": ac,
          "risk_bucket": rb
        })
        
    # Manual assets: map Fixed Deposits and Gold into holdings list with default types
    for f in fds:
        principal = f["principal"]
        curr_val = f["current_value"] or f["principal"]
        pnl = curr_val - principal
        pnl_pct = (pnl / principal * 100) if principal > 0 else 0
        
        processed_holdings.append({
          "symbol": f["name"],
          "name": f["name"],
          "asset_type": "fd",
          "quantity": f.get("quantity") or 1.0,
          "avg_cost": principal,
          "current_price": curr_val,
          "current_value": curr_val,
          "pnl": round(pnl, 2),
          "pnl_percentage": round(pnl_pct, 2),
          "sector": "DEBT",
          "instrument_type": "Fixed Deposit",
          "asset_class": "Direct listed debt",
          "risk_bucket": "Debt / liquidity"
        })
        
    for g in gold:
        principal = g["principal"]
        curr_val = g["current_value"] or g["principal"]
        pnl = curr_val - principal
        pnl_pct = (pnl / principal * 100) if principal > 0 else 0
        
        processed_holdings.append({
          "symbol": g["name"],
          "name": g["name"],
          "asset_type": "gold",
          "quantity": g["quantity"],
          "avg_cost": principal,
          "current_price": curr_val / g["quantity"] if g["quantity"] > 0 else curr_val,
          "current_value": curr_val,
          "pnl": round(pnl, 2),
          "pnl_percentage": round(pnl_pct, 2),
          "sector": "GOLD",
          "instrument_type": "Gold commodity",
          "asset_class": "Listed ETF/commodity",
          "risk_bucket": "Core/direct equity" # Gold acts as core hedge
        })

    total_value = sum(h["current_value"] for h in processed_holdings)
    
    # Calculate weight & action recommendations
    for h in processed_holdings:
        h["weight"] = (h["current_value"] / total_value * 100) if total_value > 0 else 0.0
        rec_data = holding_action(
            h["symbol"], h["sector"], h["asset_class"], h["risk_bucket"],
            h["pnl_percentage"], h["weight"]
        )
        h.update(rec_data)

    # 2. Asset Class Summaries
    ac_groups = {}
    for h in processed_holdings:
        ac = h["asset_class"]
        if ac not in ac_groups:
            ac_groups[ac] = {"name": ac, "value": 0.0, "pnl": 0.0, "count": 0}
        ac_groups[ac]["value"] += h["current_value"]
        ac_groups[ac]["pnl"] += h["pnl"]
        ac_groups[ac]["count"] += 1
        
    asset_allocation = []
    for g in ac_groups.values():
        g["value"] = round(g["value"], 2)
        g["pnl"] = round(g["pnl"], 2)
        g["weight"] = round((g["value"] / total_value * 100), 2) if total_value > 0 else 0.0
        asset_allocation.append(g)
    asset_allocation.sort(key=lambda x: x["value"], reverse=True)

    # 3. Risk Bucket Summaries
    rb_groups = {}
    for h in processed_holdings:
        rb = h["risk_bucket"]
        if rb not in rb_groups:
            rb_groups[rb] = {"name": rb, "value": 0.0, "pnl": 0.0, "count": 0}
        rb_groups[rb]["value"] += h["current_value"]
        rb_groups[rb]["pnl"] += h["pnl"]
        rb_groups[rb]["count"] += 1
        
    risk_buckets = []
    for g in rb_groups.values():
        g["value"] = round(g["value"], 2)
        g["pnl"] = round(g["pnl"], 2)
        g["weight"] = round((g["value"] / total_value * 100), 2) if total_value > 0 else 0.0
        risk_buckets.append(g)
    risk_buckets.sort(key=lambda x: x["value"], reverse=True)

    # 4. Sector Exposure (Direct equities only)
    sec_groups = {}
    for h in processed_holdings:
        sec = h["sector"]
        if sec not in sec_groups:
            sec_groups[sec] = {"name": sec, "value": 0.0, "pnl": 0.0, "count": 0}
        sec_groups[sec]["value"] += h["current_value"]
        sec_groups[sec]["pnl"] += h["pnl"]
        sec_groups[sec]["count"] += 1
        
    sector_exposure = []
    for g in sec_groups.values():
        g["value"] = round(g["value"], 2)
        g["pnl"] = round(g["pnl"], 2)
        g["weight"] = round((g["value"] / total_value * 100), 2) if total_value > 0 else 0.0
        sector_exposure.append(g)
    sector_exposure.sort(key=lambda x: x["value"], reverse=True)

    # 5. Stress Tests Shocks
    stress_tests = []
    for sc in SCENARIOS:
        loss = 0.0
        for h in processed_holdings:
            shock = sc.shocks.get(h["risk_bucket"], 0.0)
            loss += h["current_value"] * shock
            
        stress_tests.append({
            "scenario": sc.name,
            "loss": round(loss, 2),
            "loss_pct": round((loss / total_value * 100), 2) if total_value > 0 else 0.0,
            "ending_value": round(total_value + loss, 2)
        })

    # 6. Risk Warnings Flags
    flags = []
    if processed_holdings:
        # Concentration
        sorted_holdings = sorted(processed_holdings, key=lambda x: x["weight"], reverse=True)
        top = sorted_holdings[0]
        if top["weight"] > 15:
            flags.append({
                "severity": "High",
                "title": "Single holding concentration",
                "detail": f"{top['symbol']} is {top['weight']:.1f}% of your portfolio. This is opportunity-cost concentration even if the asset has low volatility."
            })
            
        # Weak debt
        weak_debt = sorted(
            [h for h in processed_holdings if h["asset_class"] == "Direct listed debt" and h["pnl_percentage"] <= -20],
            key=lambda x: x["pnl_percentage"]
        )
        if weak_debt:
            w = weak_debt[0]
            flags.append({
                "severity": "High",
                "title": "Credit/liquidity risk in listed debt",
                "detail": f"{w['symbol']} is down {w['pnl_percentage']:.1f}% and worth INR {w['current_value']:.2f}. Treat this as a credit review item, not a normal bond fluctuation."
            })
            
        # Financial services overlap
        direct_holdings = [h for h in processed_holdings if h["instrument_type"] == "-"]
        financial_val = sum(h["current_value"] for h in direct_holdings if h["sector"] == "FINANCIAL SERVICES")
        financial_weight = (financial_val / total_value * 100) if total_value > 0 else 0.0
        if financial_weight > 10:
            flags.append({
                "severity": "Medium",
                "title": "Financial services and market overlap",
                "detail": f"Financial services is {financial_weight:.1f}% of your portfolio and includes several correlated capital-market platform names."
            })
            
        # Tiny immaterial positions
        tiny_count = len([h for h in processed_holdings if h["weight"] < 0.5])
        if tiny_count >= 20:
            flags.append({
                "severity": "Medium",
                "title": "Too many immaterial positions",
                "detail": f"{tiny_count} holdings are below 0.5% weight. They add monitoring load without meaningful return impact."
            })
            
        # Under-risked
        defensive_val = sum(h["current_value"] for h in processed_holdings if h["risk_bucket"] in ["Low-vol hybrid/arbitrage", "Debt / liquidity"])
        defensive_weight = (defensive_val / total_value * 100) if total_value > 0 else 0.0
        if defensive_weight > 40:
            flags.append({
                "severity": "Medium",
                "title": "Under-risked for aggressive growth",
                "detail": f"Debt, liquid, and arbitrage-like exposure is {defensive_weight:.1f}%. Good dry powder, but high opportunity cost over 3-5 years."
            })

    # Count recommendations
    action_counts = { "Buy/Add": 0, "Hold": 0, "Trim": 0, "Exit/Review": 0 }
    for h in processed_holdings:
        rec = h["recommendation"]
        action_counts[rec] = action_counts.get(rec, 0) + 1

    return {
        "holdings": processed_holdings,
        "asset_allocation": asset_allocation,
        "risk_buckets": risk_buckets,
        "sector_exposure": sector_exposure,
        "stress_tests": stress_tests,
        "flags": flags,
        "action_counts": action_counts
    }
