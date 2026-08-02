from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, Dict

class ManualAssetBase(BaseModel):
    asset_type: str  # "FD" or "GOLD"
    name: str
    principal: float
    quantity: Optional[float] = 1.0
    interest_rate: Optional[float] = None
    compounding_frequency: Optional[str] = None
    start_date: date
    maturity_date: Optional[date] = None
    gold_type: Optional[str] = None  # "PHYSICAL", "SGB", "DIGITAL"

class ManualAssetCreate(ManualAssetBase):
    pass

class ManualAssetUpdate(BaseModel):
    name: Optional[str] = None
    principal: Optional[float] = None
    quantity: Optional[float] = None
    interest_rate: Optional[float] = None
    compounding_frequency: Optional[str] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    gold_type: Optional[str] = None
    is_active: Optional[bool] = None

class ManualAssetResponse(ManualAssetBase):
    id: int
    is_active: bool
    created_at: datetime
    current_value: Optional[float] = None  # Dynamically computed in route

    model_config = ConfigDict(from_attributes=True)

class HoldingsSnapshotResponse(BaseModel):
    id: int
    date: date
    asset_type: str
    symbol_or_scheme: str
    name: Optional[str] = None
    quantity: float
    avg_cost: float
    current_price: float
    current_value: float
    sector: Optional[str] = "-"
    instrument_type: Optional[str] = "-"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PortfolioDailyValueResponse(BaseModel):
    id: int
    date: date
    total_value: float
    value_by_asset_class: Dict[str, float]  # Parsed from JSON string in route
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PasswordVerify(BaseModel):
    password: str

class ConnectStatusResponse(BaseModel):
    connected: bool
    expires_at: Optional[datetime] = None
    user_name: Optional[str] = None
