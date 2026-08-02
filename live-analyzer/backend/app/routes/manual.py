import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import ManualAsset
from backend.app.schemas import ManualAssetCreate, ManualAssetUpdate, ManualAssetResponse
from backend.app.services.fd import calculate_fd_value
from backend.app.services.gold import get_gold_price_per_gram
from backend.app.routes.auth import verify_app_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/manual", tags=["manual_assets"], dependencies=[Depends(verify_app_session)])

def enrich_asset_value(asset: ManualAsset) -> float:
    try:
        if asset.asset_type.upper() == "FD":
            return calculate_fd_value(
                principal=asset.principal,
                interest_rate=asset.interest_rate or 0.0,
                start_date=asset.start_date,
                maturity_date=asset.maturity_date,
                compounding_frequency=asset.compounding_frequency
            )
        elif asset.asset_type.upper() == "GOLD":
            rate_per_gram = get_gold_price_per_gram()
            # current_value = grams * rate_per_gram
            return round(asset.quantity * rate_per_gram, 2)
    except Exception as e:
        logger.error(f"Error enriching asset {asset.id} value: {e}")
    return asset.principal  # Fallback to purchase price/principal

@router.get("", response_model=List[ManualAssetResponse])
def list_assets(db: Session = Depends(get_db)):
    assets = db.query(ManualAsset).filter(ManualAsset.is_active == True).all()
    response_assets = []
    for asset in assets:
        # Convert to schemas and compute current value dynamically
        curr_val = enrich_asset_value(asset)
        asset_dict = asset.__dict__.copy()
        asset_dict["current_value"] = curr_val
        response_assets.append(ManualAssetResponse(**asset_dict))
    return response_assets

@router.post("", response_model=ManualAssetResponse)
def create_asset(payload: ManualAssetCreate, db: Session = Depends(get_db)):
    # Validate FD fields
    if payload.asset_type.upper() == "FD":
        if payload.interest_rate is None or payload.interest_rate <= 0:
            raise HTTPException(status_code=400, detail="Interest rate is required for Fixed Deposits.")
        if payload.maturity_date is None:
            raise HTTPException(status_code=400, detail="Maturity date is required for Fixed Deposits.")
        if payload.maturity_date < payload.start_date:
            raise HTTPException(status_code=400, detail="Maturity date cannot be before start date.")
    
    # Validate Gold fields
    elif payload.asset_type.upper() == "GOLD":
        if payload.quantity is None or payload.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity (grams) is required for Gold.")
        if payload.gold_type is None or payload.gold_type.upper() not in ["PHYSICAL", "SGB", "DIGITAL"]:
            raise HTTPException(status_code=400, detail="Valid Gold Type (PHYSICAL, SGB, DIGITAL) is required.")

    db_asset = ManualAsset(
        asset_type=payload.asset_type.upper(),
        name=payload.name,
        principal=payload.principal,
        quantity=payload.quantity if payload.quantity is not None else 1.0,
        interest_rate=payload.interest_rate,
        compounding_frequency=payload.compounding_frequency,
        start_date=payload.start_date,
        maturity_date=payload.maturity_date,
        gold_type=payload.gold_type.upper() if payload.gold_type else None
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    
    # Enrich response
    curr_val = enrich_asset_value(db_asset)
    asset_dict = db_asset.__dict__.copy()
    asset_dict["current_value"] = curr_val
    return ManualAssetResponse(**asset_dict)

@router.put("/{asset_id}", response_model=ManualAssetResponse)
def update_asset(asset_id: int, payload: ManualAssetUpdate, db: Session = Depends(get_db)):
    db_asset = db.query(ManualAsset).filter(ManualAsset.id == asset_id, ManualAsset.is_active == True).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if key == "asset_type":
            setattr(db_asset, key, val.upper())
        elif key == "gold_type" and val:
            setattr(db_asset, key, val.upper())
        else:
            setattr(db_asset, key, val)
            
    db.commit()
    db.refresh(db_asset)
    
    curr_val = enrich_asset_value(db_asset)
    asset_dict = db_asset.__dict__.copy()
    asset_dict["current_value"] = curr_val
    return ManualAssetResponse(**asset_dict)

@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    db_asset = db.query(ManualAsset).filter(ManualAsset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Hard delete or soft delete, let's soft delete to preserve historical trend
    db_asset.is_active = False
    db.commit()
    return
