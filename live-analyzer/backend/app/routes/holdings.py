import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.routes.auth import get_connected_kite_client, get_active_session, verify_app_session
from backend.app.services.nse import get_stock_price
from backend.app.services.amfi import get_mf_nav

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/holdings", tags=["holdings"], dependencies=[Depends(verify_app_session)])

@router.get("")
def get_holdings(db: Session = Depends(get_db)):
    # Check if we have an active session
    active_session = get_active_session(db)
    if not active_session:
        return {
            "kite_connected": False,
            "stocks": [],
            "mutual_funds": []
        }
        
    try:
        kite = get_connected_kite_client(db)
        
        # 1. Fetch equity holdings
        raw_stocks = []
        try:
            raw_stocks = kite.holdings()
        except Exception as e:
            logger.error(f"Error fetching equity holdings from Kite: {e}")
            
        # 2. Fetch mutual fund holdings
        raw_mfs = []
        try:
            raw_mfs = kite.mf_holdings()
        except Exception as e:
            logger.error(f"Error fetching mutual fund holdings from Kite: {e}")

        # Process stocks
        stocks = []
        for s in raw_stocks:
            symbol = s.get("tradingsymbol")
            qty = float(s.get("quantity", 0) + s.get("t1_quantity", 0)) # Include T1 holdings
            avg_cost = float(s.get("average_price", 0))
            
            if qty <= 0:
                continue
                
            # Get live price from NSE service
            current_price = avg_cost
            try:
                current_price = get_stock_price(symbol)
            except Exception as e:
                logger.warning(f"Could not get live price for stock {symbol}, using average cost: {e}")
                
            invested_value = round(qty * avg_cost, 2)
            current_value = round(qty * current_price, 2)
            pnl = round(current_value - invested_value, 2)
            pnl_pct = round((pnl / invested_value * 100), 2) if invested_value > 0 else 0.0
            
            stocks.append({
                "symbol": symbol,
                "name": s.get("instrument_name", symbol),
                "quantity": qty,
                "average_price": avg_cost,
                "current_price": current_price,
                "invested_value": invested_value,
                "current_value": current_value,
                "pnl": pnl,
                "pnl_percentage": pnl_pct
            })

        # Process mutual funds
        mutual_funds = []
        for m in raw_mfs:
            isin = m.get("tradingsymbol") or m.get("isin")
            name = m.get("fund") or isin
            qty = float(m.get("quantity", 0))
            avg_cost = float(m.get("average_price", 0))
            
            if qty <= 0:
                continue
                
            # Get live NAV from AMFI service
            current_price = avg_cost
            try:
                current_price = get_mf_nav(isin)
            except Exception as e:
                logger.warning(f"Could not get live NAV for mutual fund {isin}, using average cost: {e}")
                
            invested_value = round(qty * avg_cost, 2)
            current_value = round(qty * current_price, 2)
            pnl = round(current_value - invested_value, 2)
            pnl_pct = round((pnl / invested_value * 100), 2) if invested_value > 0 else 0.0
            
            mutual_funds.append({
                "isin": isin,
                "name": name,
                "quantity": qty,
                "average_price": avg_cost,
                "current_price": current_price,
                "invested_value": invested_value,
                "current_value": current_value,
                "pnl": pnl,
                "pnl_percentage": pnl_pct
            })

        return {
            "kite_connected": True,
            "stocks": stocks,
            "mutual_funds": mutual_funds
        }
        
    except Exception as e:
        logger.error(f"General error in get_holdings: {e}")
        return {
            "kite_connected": False,
            "stocks": [],
            "mutual_funds": [],
            "error": str(e)
        }
