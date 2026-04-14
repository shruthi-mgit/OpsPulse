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
            min_size=2,
            max_size=10,
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

    return db_pool