import os
import sys
import json
import logging
from datetime import date
from pathlib import Path
import pandas as pd

# Setup python path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.database import SessionLocal
from backend.app.models import HoldingsSnapshot, PortfolioDailyValue, ManualAsset
from backend.app.routes.manual import enrich_asset_value

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("import_holdings")

DOWNLOADS = Path.home() / "Downloads"

def find_latest_holdings() -> Path:
    candidates = sorted(
        DOWNLOADS.glob("holdings-*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No holdings-*.xlsx file found in {DOWNLOADS}."
        )
    return candidates[0]

def clean_label(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()

def find_header_row(raw: pd.DataFrame) -> int:
    for idx, row in raw.iterrows():
        labels = {clean_label(v).lower() for v in row.tolist()}
        if "symbol" in labels and "isin" in labels:
            return int(idx)
    raise ValueError("Could not find a holdings table header row with Symbol and ISIN.")

def main():
    try:
        path = find_latest_holdings()
        logger.info(f"Found latest holdings file: {path}")
        
        xls = pd.ExcelFile(path)
        sheet = "Combined" if "Combined" in xls.sheet_names else xls.sheet_names[0]
        raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
        
        header_idx = find_header_row(raw)
        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = [clean_label(c) for c in raw.iloc[header_idx].tolist()]
        df = df.dropna(subset=["Symbol"])
        df = df.loc[:, [c for c in df.columns if c]]
        
        # Rename column if needed
        if "Unrealize P&L Pct." in df.columns:
            df = df.rename(columns={"Unrealize P&L Pct.": "Unrealized P&L Pct."})
            
        required = [
            "Symbol",
            "ISIN",
            "Sector",
            "Instrument Type",
            "Quantity Available",
            "Average Price",
            "Previous Closing Price"
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected column(s): {', '.join(missing)}")
            
        # Convert numeric columns
        for col in ["Quantity Available", "Average Price", "Previous Closing Price"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
        # Filter positive quantities
        df = df[df["Quantity Available"] > 0]
        
        db = SessionLocal()
        today = date.today()
        
        # Clear existing snapshots for today to reload
        db.query(HoldingsSnapshot).filter(HoldingsSnapshot.date == today).delete()
        
        stock_count = 0
        mf_count = 0
        total_stocks_val = 0.0
        total_mfs_val = 0.0
        
        for _, row in df.iterrows():
            symbol = str(row["Symbol"]).strip()
            isin = str(row["ISIN"]).strip()
            
            # Determine asset type
            is_mf = isin.upper().startswith("INF")
            asset_type = "mf" if is_mf else "stock"
            symbol_or_scheme = isin if is_mf else symbol
            
            qty = float(row["Quantity Available"])
            avg_cost = float(row["Average Price"])
            curr_price = float(row["Previous Closing Price"])
            current_value = round(qty * curr_price, 2)
            
            snap = HoldingsSnapshot(
                date=today,
                asset_type=asset_type,
                symbol_or_scheme=symbol_or_scheme,
                name=symbol, # Use Symbol as default name
                quantity=qty,
                avg_cost=avg_cost,
                current_price=curr_price,
                current_value=current_value,
                sector=str(row.get("Sector", "-")).strip(),
                instrument_type=str(row.get("Instrument Type", "-")).strip()
            )
            db.add(snap)
            
            if asset_type == "stock":
                stock_count += 1
                total_stocks_val += current_value
            else:
                mf_count += 1
                total_mfs_val += current_value
                
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
        
        # Write/Update the daily value
        daily_val_record = db.query(PortfolioDailyValue).filter(PortfolioDailyValue.date == today).first()
        if daily_val_record:
            daily_val_record.total_value = round(total_value, 2)
            daily_val_record.value_by_asset_class = json.dumps(value_breakdown)
        else:
            daily_val_record = PortfolioDailyValue(
                date=today,
                total_value=round(total_value, 2),
                value_by_asset_class=json.dumps(value_breakdown)
            )
            db.add(daily_val_record)
            
        db.commit()
        db.close()
        
        logger.info(f"Successfully imported {stock_count} stocks and {mf_count} mutual funds.")
        logger.info(f"Total Stocks Value: INR {total_stocks_val:,.2f}")
        logger.info(f"Total MFs Value: INR {total_mfs_val:,.2f}")
        logger.info(f"Total Net Worth recorded: INR {total_value:,.2f}")
        
    except Exception as e:
        logger.error(f"Error during import: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
