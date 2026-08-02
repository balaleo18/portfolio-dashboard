import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.routes.auth import verify_app_session
from backend.app.routes.portfolio import get_portfolio_summary
from backend.app.services.risk import calculate_risk_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(verify_app_session)])

@router.get("")
def get_portfolio_analytics(db: Session = Depends(get_db)):
    try:
        # 1. Fetch current portfolio holdings (reuses portfolio route logic)
        portfolio_data = get_portfolio_summary(db)
        assets = portfolio_data.get("assets", {})
        
        # 2. Run risk assessment engine
        metrics = calculate_risk_metrics(db, assets)
        
        return {
            "success": True,
            "total_value": metrics.get("holdings", []),
            "asset_allocation": metrics.get("asset_allocation", []),
            "risk_buckets": metrics.get("risk_buckets", []),
            "sector_exposure": metrics.get("sector_exposure", []),
            "stress_tests": metrics.get("stress_tests", []),
            "flags": metrics.get("flags", []),
            "action_counts": metrics.get("action_counts", []),
            "holdings": metrics.get("holdings", [])
        }
    except Exception as e:
        logger.error(f"Error computing portfolio analytics: {e}")
        return {
            "success": False,
            "error": str(e),
            "asset_allocation": [],
            "risk_buckets": [],
            "sector_exposure": [],
            "stress_tests": [],
            "flags": [],
            "action_counts": {},
            "holdings": []
        }
