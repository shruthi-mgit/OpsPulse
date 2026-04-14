from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.security import configure_security
from app.user_master.user_router import router as user_router
from app.onboarding.onboarding_router import router as onboarding_router
from app.Integration.payment_routes import router as payment_router
from app.scheduler.scheduler import start_scheduler

from app.database import (
    init_db,
    get_db_pool,
    init_global_database,
    seed_super_admin
)

import logging
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# ==========================================================
# LOGGING
# ==========================================================

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# ==========================================================
# LOAD ENV
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

print("Loading .env from:", env_path)

load_dotenv(dotenv_path=env_path)

print("ENV EMAIL:", os.getenv("SENDER_EMAIL"))
print("ENV PASSWORD:", "YES" if os.getenv("SENDER_PASSWORD") else "NO")

# ==========================================================
# FASTAPI APP
# ==========================================================

app = FastAPI(
    title="PayOpsB1 API",
    version="1.0.0"
)

security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# STATIC FILES (FIXED ✅)
# ==========================================================

def get_static_path():
    """
    Handles both:
    - Dev mode
    - PyInstaller EXE
    - External D drive (recommended)
    """

    # ✅ Recommended: use D drive static
    external_static = Path("D:/PayOpsUploads/static")

    if external_static.exists():
        print(f"✅ Using external static path: {external_static}")
        return str(external_static)

    # ✅ Fallback for EXE
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    internal_static = base_path / "app" / "static"

    print(f"⚠️ Using internal static path: {internal_static}")

    return str(internal_static)


STATIC_DIR = get_static_path()

# Ensure directory exists (important)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

# ==========================================================
# STARTUP
# ==========================================================

@app.on_event("startup")
async def startup():

    await init_db()
    pool = await get_db_pool()

    app.state.db_pool = pool

    async with pool.acquire() as conn:
        await init_global_database(conn)
        await seed_super_admin(conn)

    # Start scheduler
    start_scheduler(pool)

    print("✅ Application startup completed")

# ==========================================================
# SECURITY
# ==========================================================

configure_security(app)

# ==========================================================
# ROUTERS
# ==========================================================

app.include_router(user_router, prefix="/payopsb1/api/user_master")
app.include_router(onboarding_router, prefix="/payopsb1/api")
app.include_router(payment_router, prefix="/payopsb1/api")

# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get("/")
def root():
    return {"status": "PayOpsB1 API Running"}

# ==========================================================
# ENV VARIABLES
# ==========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

SECRET_KEY = os.getenv(
    "PayOpsB1_SuperSecure_JWT_Secret_Key_2026_Production"
)

# ==========================================================
# RUN SERVER
# ==========================================================

if __name__ == "__main__":

    import uvicorn

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", "8083"))

    print(f"🚀 Starting server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False
    )