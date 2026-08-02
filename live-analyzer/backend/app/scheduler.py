import logging
import json
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import PortfolioDailyValue, HoldingsSnapshot, ManualAsset
from backend.app.routes.holdings import get_holdings
from backend.app.routes.manual import enrich_asset_value

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def take_portfolio_snapshot():
    db = SessionLocal()
    try:
        today = date.today()
        logger.info(f"Starting daily portfolio snapshot for {today}...")
        
        # 1. Fetch current holdings (attempts Kite Connect)
        holdings_data = get_holdings(db)
        stocks = holdings_data.get("stocks", [])
        mfs = holdings_data.get("mutual_funds", [])
        kite_connected = holdings_data.get("kite_connected", False)
        
        if kite_connected:
            # Delete any existing snapshots for today to avoid duplicate constraint errors
            db.query(HoldingsSnapshot).filter(HoldingsSnapshot.date == today).delete()
            
            from backend.app.services.risk import resolve_sector_and_type
            for s in stocks:
                sector, inst_type = resolve_sector_and_type(db, s["symbol"], "stock")
                snap = HoldingsSnapshot(
                    date=today,
                    asset_type="stock",
                    symbol_or_scheme=s["symbol"],
                    name=s["name"],
                    quantity=s["quantity"],
                    avg_cost=s["average_price"],
                    current_price=s["current_price"],
                    current_value=s["current_value"],
                    sector=sector,
                    instrument_type=inst_type
                )
                db.add(snap)
                
            for m in mfs:
                sector, inst_type = resolve_sector_and_type(db, m["isin"], "mf")
                snap = HoldingsSnapshot(
                    date=today,
                    asset_type="mf",
                    symbol_or_scheme=m["isin"],
                    name=m["name"],
                    quantity=m["quantity"],
                    avg_cost=m["average_price"],
                    current_price=m["current_price"],
                    current_value=m["current_value"],
                    sector=sector,
                    instrument_type=inst_type
                )
                db.add(snap)
            db.commit()
            logger.info("Saved latest holdings snapshots from Kite Connect.")
        else:
            # Carry forward the most recent snapshot day
            latest_snap_date = db.query(HoldingsSnapshot.date).order_by(HoldingsSnapshot.date.desc()).first()
            if latest_snap_date:
                latest_date = latest_snap_date[0]
                existing_today = db.query(HoldingsSnapshot).filter(HoldingsSnapshot.date == today).first()
                
                # If we don't have a snapshot for today, copy the latest one with refreshed prices
                if not existing_today and latest_date != today:
                    logger.info(f"Kite disconnected. Carrying forward snapshots from {latest_date} with updated prices.")
                    prev_snaps = db.query(HoldingsSnapshot).filter(HoldingsSnapshot.date == latest_date).all()
                    
                    for prev in prev_snaps:
                        curr_price = prev.current_price
                        try:
                            if prev.asset_type == "stock":
                                from backend.app.services.nse import get_stock_price
                                curr_price = get_stock_price(prev.symbol_or_scheme)
                            elif prev.asset_type == "mf":
                                from backend.app.services.amfi import get_mf_nav
                                curr_price = get_mf_nav(prev.symbol_or_scheme)
                        except Exception as pe:
                            logger.warning(f"Failed to update price for carried asset {prev.symbol_or_scheme}: {pe}")
                            
                        new_snap = HoldingsSnapshot(
                            date=today,
                            asset_type=prev.asset_type,
                            symbol_or_scheme=prev.symbol_or_scheme,
                            name=prev.name,
                            quantity=prev.quantity,
                            avg_cost=prev.avg_cost,
                            current_price=curr_price,
                            current_value=round(prev.quantity * curr_price, 2),
                            sector=prev.sector,
                            instrument_type=prev.instrument_type
                        )
                        db.add(new_snap)
                    db.commit()
        
        # Recalculate valuations based on today's snapshots
        today_snaps = db.query(HoldingsSnapshot).filter(HoldingsSnapshot.date == today).all()
        total_stocks_val = sum(s.current_value for s in today_snaps if s.asset_type == "stock")
        total_mfs_val = sum(m.current_value for m in today_snaps if m.asset_type == "mf")
        
        # 2. Get manual assets valuations
        manual_assets = db.query(ManualAsset).filter(ManualAsset.is_active == True).all()
        total_fds_val = 0.0
        total_gold_val = 0.0
        
        for asset in manual_assets:
            val = enrich_asset_value(asset)
            if asset.asset_type.upper() == "FD":
                total_fds_val += val
            elif asset.asset_type.upper() == "GOLD":
                total_gold_val += val
                
        total_value = total_stocks_val + total_mfs_val + total_fds_val + total_gold_val
        value_breakdown = {
            "stocks": round(total_stocks_val, 2),
            "mutual_funds": round(total_mfs_val, 2),
            "fixed_deposits": round(total_fds_val, 2),
            "gold": round(total_gold_val, 2)
        }
        
        # Compute risk bucket allocations and flag count for snapshot history
        from backend.app.services.risk import calculate_risk_metrics
        assets_payload = {
            "stocks": [
                {
                    "symbol": s.symbol_or_scheme,
                    "name": s.name,
                    "quantity": s.quantity,
                    "average_price": s.avg_cost,
                    "current_price": s.current_price,
                    "current_value": s.current_value,
                    "pnl": round(s.current_value - s.quantity * s.avg_cost, 2),
                    "pnl_percentage": round(((s.current_value - s.quantity * s.avg_cost) / (s.quantity * s.avg_cost) * 100), 2) if s.avg_cost > 0 else 0
                } for s in today_snaps if s.asset_type == "stock"
            ],
            "mutual_funds": [
                {
                    "isin": m.symbol_or_scheme,
                    "name": m.name,
                    "quantity": m.quantity,
                    "average_price": m.avg_cost,
                    "current_price": m.current_price,
                    "current_value": m.current_value,
                    "pnl": round(m.current_value - m.quantity * m.avg_cost, 2),
                    "pnl_percentage": round(((m.current_value - m.quantity * m.avg_cost) / (m.quantity * m.avg_cost) * 100), 2) if m.avg_cost > 0 else 0
                } for m in today_snaps if m.asset_type == "mf"
            ],
            "fixed_deposits": [
                {
                    "name": f.name,
                    "principal": f.principal,
                    "current_value": enrich_asset_value(f),
                    "start_date": f.start_date,
                    "quantity": f.quantity
                } for f in manual_assets if f.asset_type.upper() == "FD"
            ],
            "gold": [
                {
                    "name": g.name,
                    "principal": g.principal,
                    "current_value": enrich_asset_value(g),
                    "start_date": g.start_date,
                    "quantity": g.quantity
                } for g in manual_assets if g.asset_type.upper() == "GOLD"
            ]
        }
        
        try:
            metrics = calculate_risk_metrics(db, assets_payload)
            risk_buckets_breakdown = {g["name"]: round(g["value"], 2) for g in metrics.get("risk_buckets", [])}
            flag_count = len(metrics.get("flags", []))
        except Exception as re:
            logger.error(f"Error calculating risk metrics in scheduler: {re}")
            risk_buckets_breakdown = {}
            flag_count = 0

        # Write/Update the daily value
        daily_val_record = db.query(PortfolioDailyValue).filter(PortfolioDailyValue.date == today).first()
        if daily_val_record:
            daily_val_record.total_value = round(total_value, 2)
            daily_val_record.value_by_asset_class = json.dumps(value_breakdown)
            daily_val_record.value_by_risk_bucket = json.dumps(risk_buckets_breakdown)
            daily_val_record.flag_count = flag_count
        else:
            daily_val_record = PortfolioDailyValue(
                date=today,
                total_value=round(total_value, 2),
                value_by_asset_class=json.dumps(value_breakdown),
                value_by_risk_bucket=json.dumps(risk_buckets_breakdown),
                flag_count=flag_count
            )
            db.add(daily_val_record)
            
        db.commit()
        logger.info(f"Recorded daily portfolio snapshot successfully: Total = INR {total_value:.2f}")
        
    except Exception as e:
        logger.error(f"Error executing daily portfolio snapshot: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Schedule the job to run every day at 11:30 PM local/server time
        scheduler.add_job(
            take_portfolio_snapshot,
            trigger="cron",
            hour=23,
            minute=30,
            id="daily_portfolio_snapshot"
        )
        scheduler.start()
        logger.info("Background scheduler started successfully.")
        
        # Trigger immediate snapshot in background on startup if not already recorded today
        db = SessionLocal()
        try:
            today = date.today()
            existing = db.query(PortfolioDailyValue).filter(PortfolioDailyValue.date == today).first()
            if not existing:
                logger.info("No snapshot found for today. Queueing startup snapshot.")
                scheduler.add_job(take_portfolio_snapshot, id="startup_snapshot")
        finally:
            db.close()
