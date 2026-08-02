import logging
from datetime import datetime, time, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from kiteconnect import KiteConnect
import bcrypt
import jwt

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models import KiteSession
from backend.app.security import encrypt_token, decrypt_token
from backend.app.schemas import ConnectStatusResponse, PasswordVerify

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

def verify_app_session(authorization: Optional[str] = Header(None)):
    # Bypass if password hash is not configured
    if settings.APP_PASSWORD_HASH in ["your_bcrypt_hashed_password_here", ""]:
        return
        
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing or invalid. Please login."
        )
        
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.ENCRYPTION_KEY, algorithms=["HS256"])
        exp = payload.get("exp")
        if not exp or datetime.utcnow().timestamp() > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please login again.")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token.")


def get_kite_client():
    return KiteConnect(api_key=settings.KITE_API_KEY)

def get_active_session(db: Session):
    now = datetime.utcnow()
    # Find latest session that has not expired
    session = db.query(KiteSession).filter(KiteSession.expires_at > now).order_by(KiteSession.id.desc()).first()
    return session

def get_connected_kite_client(db: Session):
    session = get_active_session(db)
    if not session:
        raise HTTPException(status_code=401, detail="Kite Connect session expired or not established. Please reconnect.")
    
    access_token = decrypt_token(session.encrypted_access_token)
    if not access_token:
        raise HTTPException(status_code=401, detail="Failed to decrypt access token. Please reconnect.")
    
    kite = get_kite_client()
    kite.set_access_token(access_token)
    return kite

@router.get("/status", response_model=ConnectStatusResponse)
def get_status(db: Session = Depends(get_db)):
    session = get_active_session(db)
    if not session:
        return ConnectStatusResponse(connected=False)
    
    return ConnectStatusResponse(
        connected=True,
        expires_at=session.expires_at
    )

@router.get("/login-url")
def get_login_url():
    url = f"https://kite.zerodha.com/connect/login?api_key={settings.KITE_API_KEY}&v=3"
    return {"url": url}

@router.get("/callback")
def auth_callback(request_token: str, db: Session = Depends(get_db)):
    if not request_token:
        raise HTTPException(status_code=400, detail="Missing request_token")
    
    try:
        kite = get_kite_client()
        data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
        
        # Save session
        access_token = data["access_token"]
        encrypted_token = encrypt_token(access_token)
        
        # Set expiry to next day at 6:00 AM local/UTC
        # Kite tokens generally expire at 6 AM local time. We'll set it to next day 6:00 AM.
        now = datetime.utcnow()
        tomorrow = now + timedelta(days=1)
        expires_at = datetime.combine(tomorrow.date(), time(6, 0))
        
        db_session = KiteSession(
            encrypted_access_token=encrypted_token,
            public_token=data.get("public_token"),
            expires_at=expires_at,
            generated_at=now
        )
        db.add(db_session)
        db.commit()
        
        logger.info("Successfully established and encrypted Kite Connect session.")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?connected=true")
        
    except Exception as e:
        logger.error(f"Error during Kite Connect auth callback: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?error=auth_failed")

@router.post("/login")
def login(payload: PasswordVerify):
    # If not configured, allow bypass
    if settings.APP_PASSWORD_HASH in ["your_bcrypt_hashed_password_here", ""]:
        token = jwt.encode(
            {"exp": (datetime.utcnow() + timedelta(days=7)).timestamp()},
            settings.ENCRYPTION_KEY,
            algorithm="HS256"
        )
        return {"token": token, "bypass": True}
        
    password_bytes = payload.password.encode("utf-8")
    hash_bytes = settings.APP_PASSWORD_HASH.encode("utf-8")
    
    try:
        if bcrypt.checkpw(password_bytes, hash_bytes):
            token = jwt.encode(
                {"exp": (datetime.utcnow() + timedelta(days=7)).timestamp()},
                settings.ENCRYPTION_KEY,
                algorithm="HS256"
            )
            return {"token": token, "bypass": False}
    except Exception as e:
        logger.error(f"App login error: {e}")
        
    raise HTTPException(status_code=401, detail="Invalid password")

