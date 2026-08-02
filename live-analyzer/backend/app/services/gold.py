import logging
import time
from datetime import date
import yfinance as yf

logger = logging.getLogger(__name__)

# Cache gold price per gram for the day
_gold_price_cache = None
_last_update_date = None

def get_gold_price_per_gram() -> float:
    global _gold_price_cache, _last_update_date
    today = date.today()
    
    if _gold_price_cache is not None and _last_update_date == today:
        return _gold_price_cache
        
    try:
        logger.info("Fetching gold price and USD/INR rate from yfinance...")
        
        # 1. Fetch Gold Futures (GC=F) in USD/oz
        gold_ticker = yf.Ticker("GC=F")
        gold_hist = gold_ticker.history(period="1d")
        if gold_hist.empty:
            raise ValueError("Failed to retrieve history for GC=F")
        gold_usd_per_oz = float(gold_hist["Close"].iloc[-1])
        
        # 2. Fetch USD/INR exchange rate (INR=X)
        inr_ticker = yf.Ticker("INR=X")
        inr_hist = inr_ticker.history(period="1d")
        if inr_hist.empty:
            raise ValueError("Failed to retrieve history for INR=X")
        usd_inr_rate = float(inr_hist["Close"].iloc[-1])
        
        # 3. Convert Troy Ounce (31.1035 grams) to Grams
        price_per_gram_inr = (gold_usd_per_oz * usd_inr_rate) / 31.1035
        
        _gold_price_cache = price_per_gram_inr
        _last_update_date = today
        
        logger.info(f"Fetched gold price per gram: INR {price_per_gram_inr:.2f} (Gold USD: {gold_usd_per_oz:.2f}, USDINR: {usd_inr_rate:.2f})")
        return price_per_gram_inr
        
    except Exception as e:
        logger.error(f"Error calculating gold price per gram: {e}")
        # Default fallback gold price (e.g. standard ~INR 7500 per gram as of early 2026/late 2025)
        # We can also return the last cached price if it exists
        if _gold_price_cache is not None:
            logger.info(f"Using stale cached gold price: {_gold_price_cache:.2f}")
            return _gold_price_cache
        
        # Absolute fallback to keep the app working
        fallback_price = 7500.0
        logger.warning(f"Using absolute fallback gold price: INR {fallback_price:.2f}")
        return fallback_price
