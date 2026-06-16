from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.security import configure_security
from app.user_master.user_router import router as user_router
from app.onboarding.onboarding_router import router as onboarding_router
from app.Integration.payment_routes import router as payment_router
from app.scheduler.scheduler import start_scheduler
from app.scheduler.log_router import router as log_router
#from app.core.trial_guard import init_trial
from app.Integration.inventory_router import router as inventory_router
from app.Integration.upi_routes import router as upi_router
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

sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
sys.stderr.reconfigure(encoding="utf-8", errors="ignore")

# ==========================================================
# LOGGING
# ==========================================================

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# ==========================================================
# LOAD ENV
# ==========================================================

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    # running as EXE → use current folder
    BASE_DIR = Path(os.getcwd())
else:
    # normal run
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
    title="OpsPulseB1 API",
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


if getattr(sys, 'frozen', False):
    # EXE mode → PyInstaller temp folder
    BASE_PATH = Path(sys._MEIPASS)
else:
    # normal mode
    BASE_PATH = Path(__file__).resolve().parent

STATIC_DIR = BASE_PATH / "static"

print("STATIC DIR:", STATIC_DIR)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
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

    

    print("Application startup completed")

#init_trial(app)

# ==========================================================
# SECURITY
# ==========================================================

configure_security(app)

# ==========================================================
# ROUTERS
# ==========================================================

app.include_router(user_router, prefix="/Opspulseb1/api/user_master")
app.include_router(onboarding_router, prefix="/Opspulseb1/api")
app.include_router(payment_router, prefix="/Opspulseb1/api")
app.include_router(log_router, prefix="/Opspulseb1/api")
app.include_router(inventory_router, prefix="/Opspulseb1/api")
app.include_router(upi_router,prefix="/Opspulseb1/api")

# ==========================================================
# HEALTH CHECK
# ==========================================================

@app.get("/")
def root():
    return {"status": "OpspulseB1 API Running"}

# ==========================================================
# ENV VARIABLES
# ==========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

SECRET_KEY = os.getenv(
    "OpspulseB1_SuperSecure_JWT_Secret_Key_2026_Production"
)

# ==========================================================
# RUN SERVER
# ==========================================================

if __name__ == "__main__":

    import uvicorn

    host = os.getenv("UVICORN_HOST", "0.0.0.0")
    port = int(os.getenv("UVICORN_PORT", "8089"))

    print(f"Starting server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False
    )