import json
import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.routes.holdings import get_holdings
from backend.app.routes.manual import list_assets, enrich_asset_value
from backend.app.services.xirr import calculate_xirr
from backend.app.models import PortfolioDailyValue
from backend.app.routes.auth import verify_app_session

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"], dependencies=[Depends(verify_app_session)])

@router.get("/summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    # 1. Fetch stock & mutual fund holdings
    holdings_data = get_holdings(db)
    stocks = holdings_data.get("stocks", [])
    mfs = holdings_data.get("mutual_funds", [])
    kite_connected = holdings_data.get("kite_connected", False)
    
    # 2. Fetch manual assets
    manual_assets_list = list_assets(db)
    
    fds = []
    gold_items = []
    
    for asset in manual_assets_list:
        asset_dict = asset.model_dump()
        if asset.asset_type.upper() == "FD":
            # Calculate XIRR for individual FD
            cash_flows = [
                (asset.start_date, -asset.principal),
                (datetime.date.today(), asset.current_value or asset.principal)
            ]
            asset_dict["xirr"] = calculate_xirr(cash_flows)
            fds.append(asset_dict)
        elif asset.asset_type.upper() == "GOLD":
            # Calculate XIRR for individual Gold entry
            cash_flows = [
                (asset.start_date, -asset.principal),
                (datetime.date.today(), asset.current_value or asset.principal)
            ]
            asset_dict["xirr"] = calculate_xirr(cash_flows)
            gold_items.append(asset_dict)

    # 3. Calculate portfolio aggregates
    total_stock_invested = sum(s["invested_value"] for s in stocks)
    total_stock_current = sum(s["current_value"] for s in stocks)
    
    total_mf_invested = sum(m["invested_value"] for m in mfs)
    total_mf_current = sum(m["current_value"] for m in mfs)
    
    total_fd_invested = sum(f["principal"] for f in fds)
    total_fd_current = sum(f["current_value"] for f in fds)
    
    total_gold_invested = sum(g["principal"] for g in gold_items)
    total_gold_current = sum(g["current_value"] for g in gold_items)
    
    net_worth = total_stock_current + total_mf_current + total_fd_current + total_gold_current
    total_invested = total_stock_invested + total_mf_invested + total_fd_invested + total_gold_invested
    total_pnl = net_worth - total_invested
    total_pnl_percentage = round((total_pnl / total_invested * 100), 2) if total_invested > 0 else 0.0

    # 4. Formulate asset allocation
    allocation = {
        "stocks": round(total_stock_current, 2),
        "mutual_funds": round(total_mf_current, 2),
        "fixed_deposits": round(total_fd_current, 2),
        "gold": round(total_gold_current, 2)
    }
    
    allocation_percentage = {}
    for key, val in allocation.items():
        allocation_percentage[key] = round((val / net_worth * 100), 2) if net_worth > 0 else 0.0

    # 5. Fetch historical trend data
    history = db.query(PortfolioDailyValue).order_by(PortfolioDailyValue.date.asc()).all()
    trend = []
    for h in history:
        try:
            val_by_class = json.loads(h.value_by_asset_class)
        except Exception:
            val_by_class = {}
            
        trend.append({
            "date": h.date.isoformat(),
            "total_value": h.total_value,
            **val_by_class
        })

    return {
        "net_worth": round(net_worth, 2),
        "total_invested": round(total_invested, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_percentage": total_pnl_percentage,
        "kite_connected": kite_connected,
        "allocation": allocation,
        "allocation_percentage": allocation_percentage,
        "assets": {
            "stocks": stocks,
            "mutual_funds": mfs,
            "fixed_deposits": fds,
            "gold": gold_items
        },
        "trend": trend
    }
