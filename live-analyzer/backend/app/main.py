import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.routes import auth, holdings, manual, portfolio, analytics
from backend.app.scheduler import start_scheduler


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize DB tables
try:
    Base.metadata.create_all(bind=engine)
    
    # Self-healing migrations for SQLite columns
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check holdings_snapshots
        try:
            conn.execute(text("SELECT sector FROM holdings_snapshots LIMIT 1"))
        except Exception:
            conn.execute(text("ALTER TABLE holdings_snapshots ADD COLUMN sector VARCHAR(100) DEFAULT '-'"))
            conn.execute(text("ALTER TABLE holdings_snapshots ADD COLUMN instrument_type VARCHAR(100) DEFAULT '-'"))
            conn.commit()
            logger.info("Migrated holdings_snapshots (added sector & instrument_type).")

        # Check portfolio_daily_values
        try:
            conn.execute(text("SELECT value_by_risk_bucket FROM portfolio_daily_values LIMIT 1"))
        except Exception:
            conn.execute(text("ALTER TABLE portfolio_daily_values ADD COLUMN value_by_risk_bucket TEXT"))
            conn.execute(text("ALTER TABLE portfolio_daily_values ADD COLUMN flag_count INTEGER DEFAULT 0"))
            conn.commit()
            logger.info("Migrated portfolio_daily_values (added value_by_risk_bucket & flag_count).")
            
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database tables: {e}")

app = FastAPI(
    title="Personal Investment Portfolio Dashboard API",
    description="Backend API for personal net-worth tracking across Zerodha holdings and manual assets.",
    version="1.0.0"
)

# Restricted CORS to frontend url
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(holdings.router)
app.include_router(manual.router)
app.include_router(portfolio.router)
app.include_router(analytics.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "kite_api_key_configured": settings.KITE_API_KEY != "your_kite_api_key",
        "encryption_key_configured": settings.ENCRYPTION_KEY != "your_fernet_encryption_key_here",
        "app_password_configured": settings.APP_PASSWORD_HASH != "your_bcrypt_hashed_password_here"
    }

@app.on_event("startup")
def startup_event():
    logger.info("Starting background scheduler...")
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
