import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, Text
from backend.app.database import Base

class KiteSession(Base):
    __tablename__ = "kite_sessions"

    id = Column(Integer, primary_key=True, index=True)
    encrypted_access_token = Column(Text, nullable=False)
    public_token = Column(String(255), nullable=True) # Kite request token or public token
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class ManualAsset(Base):
    __tablename__ = "manual_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String(50), nullable=False)  # "FD" or "GOLD"
    name = Column(String(255), nullable=False)        # E.g. "HDFC Bank FD", "Physical Gold Coins"
    
    # Financial fields
    principal = Column(Float, nullable=False)         # Principal for FD / Purchase Price for Gold
    quantity = Column(Float, default=1.0)             # 1.0 for FD, grams/weight for Gold
    interest_rate = Column(Float, nullable=True)      # For FD (annual percentage, e.g. 7.5)
    compounding_frequency = Column(String(50), nullable=True) # "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Cumulative"
    
    # Dates
    start_date = Column(Date, nullable=False)         # Start Date / Purchase Date
    maturity_date = Column(Date, nullable=True)       # Maturity Date (FD only)
    
    # Metadata
    gold_type = Column(String(50), nullable=True)     # "PHYSICAL", "SGB", "DIGITAL" (Gold only)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class HoldingsSnapshot(Base):
    __tablename__ = "holdings_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)   # "stock" or "mf"
    symbol_or_scheme = Column(String(100), nullable=False) # Trading symbol (stocks) or Scheme code (MFs)
    name = Column(String(255), nullable=True)
    quantity = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    sector = Column(String(100), nullable=True, default="-")
    instrument_type = Column(String(100), nullable=True, default="-")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PortfolioDailyValue(Base):
    __tablename__ = "portfolio_daily_values"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    total_value = Column(Float, nullable=False)
    value_by_asset_class = Column(Text, nullable=False) # JSON string: {"stock": X, "mf": Y, "fd": Z, "gold": W}
    value_by_risk_bucket = Column(Text, nullable=True)   # JSON string: {"Debt / liquidity": X, ...}
    flag_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
