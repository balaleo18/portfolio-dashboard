import logging
import io
from datetime import date
import requests
import pandas as pd

logger = logging.getLogger(__name__)

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

# Cache structure: {scheme_code (str): nav (float)}
_nav_cache = {}
_last_update_date = None

def fetch_and_cache_navs() -> dict:
    global _nav_cache, _last_update_date
    today = date.today()
    
    # If cache is valid for today, return it
    if _nav_cache and _last_update_date == today:
        return _nav_cache
        
    try:
        logger.info("Fetching daily NAV file from AMFI...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(AMFI_NAV_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        # Read text line by line to parse
        content = response.text
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            # Each data line must contain at least 4 fields (Scheme Code; ISIN; ISIN2; Scheme Name; NAV; Sale; Repurchase; Date)
            if ";" in line:
                lines.append(line)
                
        if not lines:
            raise ValueError("No data lines containing ';' found in AMFI file.")
            
        # Parse with pandas
        # Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
        # Header is usually: Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
        csv_data = "\n".join(lines)
        df = pd.read_csv(io.StringIO(csv_data), sep=";", on_bad_lines="skip")
        
        # Strip whitespaces from column names
        df.columns = [col.strip() for col in df.columns]
        
        # Clean scheme code: must be numeric
        df["Scheme Code"] = pd.to_numeric(df["Scheme Code"], errors="coerce")
        df = df.dropna(subset=["Scheme Code"])
        
        new_cache = {}
        for _, row in df.iterrows():
            nav_val_str = str(row.get("Net Asset Value", "")).strip()
            try:
                nav = float(nav_val_str)
            except ValueError:
                continue
                
            # Map scheme code
            scheme_code = str(int(row["Scheme Code"])).strip()
            new_cache[scheme_code] = nav
            
            # Map ISINs if present
            # Column names in AMFI file are: ISIN Div Payout/ ISIN Growth, ISIN Div Reinvestment
            isin_growth = str(row.get("ISIN Div Payout/ ISIN Growth", "")).strip()
            isin_reinv = str(row.get("ISIN Div Reinvestment", "")).strip()
            
            if isin_growth and isin_growth.upper() != "N.A.":
                new_cache[isin_growth.upper()] = nav
            if isin_reinv and isin_reinv.upper() != "N.A.":
                new_cache[isin_reinv.upper()] = nav
                
        if new_cache:
            _nav_cache = new_cache
            _last_update_date = today
            logger.info(f"Successfully cached {len(_nav_cache)} mutual fund NAVs/ISINs from AMFI.")
        else:
            logger.warning("Parsed AMFI file but did not cache any valid NAVs.")
            
    except Exception as e:
        logger.error(f"Error fetching AMFI NAVs: {e}")
        if not _nav_cache:
            logger.warning("No AMFI NAV cache available.")
            
    return _nav_cache

def get_mf_nav(key: str) -> float:
    # Convert key to string and uppercase (for ISIN lookup)
    key_str = str(key).strip().upper()
    cache = fetch_and_cache_navs()
    
    if key_str in cache:
        return cache[key_str]
        
    raise ValueError(f"Could not find Mutual Fund NAV for Scheme Code/ISIN: {key}")
