import logging
import time
from jugaad_data.nse import NSELive
import yfinance as yf

logger = logging.getLogger(__name__)

# Basic in-memory cache: {symbol: (price, timestamp)}
_price_cache = {}
CACHE_EXPIRY_SECONDS = 900  # 15 minutes

def get_stock_price(symbol: str) -> float:
    symbol = symbol.strip().upper()
    now = time.time()
    
    # Check cache
    if symbol in _price_cache:
        price, ts = _price_cache[symbol]
        if now - ts < CACHE_EXPIRY_SECONDS:
            return price

    # 1. Try jugaad-data (NSELive)
    try:
        n = NSELive()
        quote = n.stock_quote(symbol)
        if quote and 'priceInfo' in quote and 'lastPrice' in quote['priceInfo']:
            price = float(quote['priceInfo']['lastPrice'])
            _price_cache[symbol] = (price, now)
            logger.info(f"Fetched price for {symbol} from NSELive: {price}")
            return price
    except Exception as e:
        logger.warning(f"Failed to fetch price for {symbol} from NSELive: {e}. Trying yfinance fallback.")

    # 2. Try yfinance fallback
    try:
        yf_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        
        if price is None:
            # Fallback to daily history
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                
        if price is not None:
            price = float(price)
            _price_cache[symbol] = (price, now)
            logger.info(f"Fetched price for {symbol} from yfinance: {price}")
            return price
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol} from yfinance: {e}")

    # 3. Fallback to expired cache value if available
    if symbol in _price_cache:
        logger.info(f"Using expired cached price for {symbol}: {_price_cache[symbol][0]}")
        return _price_cache[symbol][0]

    raise ValueError(f"Could not fetch price for symbol: {symbol}")
