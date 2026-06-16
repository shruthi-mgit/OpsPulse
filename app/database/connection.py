import asyncpg
import os
import logging
from dotenv import load_dotenv
from pathlib import Path
import sys

logger = logging.getLogger("database")

# =========================
# LOAD ENV (WORKS FOR EXE + NORMAL)
# =========================

if getattr(sys, "frozen", False):
    # running as EXE
    BASE_DIR = Path(sys.executable).parent
else:
    # running as python
    BASE_DIR = Path(__file__).resolve().parent.parent

env_path = BASE_DIR / ".env"

print("ENV PATH:", env_path)

load_dotenv(env_path)

print("DATABASE_URL:", os.getenv("DATABASE_URL"))


# =========================
# DATABASE CONFIG
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")


db_pool: asyncpg.Pool = None


# =========================
# INIT DB
# =========================

async def init_db():

    global db_pool

    try:
        logger.info("Creating DB pool...")

        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=30,
            max_inactive_connection_lifetime=300,
            command_timeout=60
        )

        async with db_pool.acquire() as conn:
            await conn.execute("SELECT 1")

        logger.info("Database pool created")

    except Exception as e:
        logger.error(e)
        raise


# =========================
# GET POOL
# =========================

async def get_db_pool():

    if db_pool is None:
        raise RuntimeError("DB pool not ready")

    logger.info(
        f"Pool Size={db_pool.get_size()} "
        f"Idle={db_pool.get_idle_size()}"
    )

    return db_pool

ICICI_BASE_URL = os.getenv("ICICI_BASE_URL")
ICICI_PFX_PASSWORD = os.getenv("ICICI_PFX_PASSWORD")
ICICI_CERT_FILE = os.getenv("ICICI_CERT_FILE")
ICICI_PFX_FILE = os.getenv("ICICI_PFX_FILE")

if not ICICI_BASE_URL:
    raise RuntimeError("ICICI_BASE_URL not set")

if not ICICI_PFX_PASSWORD:
    raise RuntimeError("ICICI_PFX_PASSWORD not set")

if not ICICI_CERT_FILE:
    raise RuntimeError("ICICI_CERT_FILE not set")

if not ICICI_PFX_FILE:
    raise RuntimeError("ICICI_PFX_FILE not set")

print("ICICI_BASE_URL =", ICICI_BASE_URL)
print("ICICI_CERT_FILE =", ICICI_CERT_FILE)
print("ICICI_PFX_FILE =", ICICI_PFX_FILE)
print("ICICI_PFX_PASSWORD exists =", bool(ICICI_PFX_PASSWORD))