# import base64
# import struct
# import time
# import logging
# import asyncio
# import hashlib
# import uuid
# import os
# import platform
# from fastapi import HTTPException
# from fastapi.responses import JSONResponse

# logger = logging.getLogger("trial-guard")

# # ==============================
# # CONFIG
# # ==============================
# _TRIAL_DAYS = 30
# _SECONDS_PER_DAY = 86400  # testing (change to 86400 for production)

# # Registry (SYSTEM-WIDE)
# _REG_KEY_PATH = r"SOFTWARE\OpsPulseB1\Trial"
# _REG_TS = "install_ts"
# _REG_HASH = "install_hash"

# # File backup
# TRIAL_FILE = os.getenv(
#     "TRIAL_FILE_PATH",
#     r"C:\ProgramData\OpsPulseB1\.trial"
# )

# # ==============================
# # MACHINE FINGERPRINT
# # ==============================
# def _machine_fingerprint():
#     raw = f"{uuid.getnode()}-{platform.node()}-{platform.system()}"
#     return hashlib.sha256(raw.encode()).hexdigest()


# def _hash(ts: float):
#     raw = f"{ts}-{_machine_fingerprint()}".encode()
#     return hashlib.sha256(raw).hexdigest()


# # ==============================
# # REGISTRY (FIXED → HKLM)
# # ==============================
# def _read_reg():
#     try:
#         import winreg

#         with winreg.OpenKey(
#             winreg.HKEY_LOCAL_MACHINE,
#             _REG_KEY_PATH,
#             0,
#             winreg.KEY_READ | winreg.KEY_WOW64_64KEY
#         ) as k:

#             raw_ts, _ = winreg.QueryValueEx(k, _REG_TS)
#             raw_hash, _ = winreg.QueryValueEx(k, _REG_HASH)

#             try:
#                 ts = struct.unpack(">d", base64.b64decode(raw_ts))[0]
#             except Exception:
#                 logger.error("[trial] invalid registry data")
#                 raise HTTPException(403, "Trial tampering detected")

#             return ts, raw_hash

#     except FileNotFoundError:
#         return None, None

#     except HTTPException:
#         raise

#     except Exception as e:
#         logger.error(f"[trial] registry read error: {e}")
#         return None, None


# def _write_reg(ts: float):
#     try:
#         import winreg

#         encoded_ts = base64.b64encode(struct.pack(">d", ts)).decode()
#         h = _hash(ts)

#         logger.info("[trial] writing registry...")

#         with winreg.CreateKeyEx(
#             winreg.HKEY_LOCAL_MACHINE,
#             _REG_KEY_PATH,
#             0,
#             winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
#         ) as k:
#             winreg.SetValueEx(k, _REG_TS, 0, winreg.REG_SZ, encoded_ts)
#             winreg.SetValueEx(k, _REG_HASH, 0, winreg.REG_SZ, h)

#         logger.info("[trial] registry write SUCCESS")

#     except Exception as e:
#         logger.error(f"[trial] registry write FAILED: {e}")


# # ==============================
# # FILE BACKUP
# # ==============================
# def _read_file():
#     try:
#         if not os.path.exists(TRIAL_FILE):
#             return None, None

#         with open(TRIAL_FILE, "r") as f:
#             ts_str, h = f.read().split("|")

#             try:
#                 ts = float(ts_str)
#             except Exception:
#                 logger.error("[trial] invalid file data")
#                 raise HTTPException(403, "Trial tampering detected")

#             return ts, h

#     except HTTPException:
#         raise

#     except Exception as e:
#         logger.error(f"[trial] file read error: {e}")
#         return None, None


# def _write_file(ts: float):
#     try:
#         os.makedirs(os.path.dirname(TRIAL_FILE), exist_ok=True)

#         with open(TRIAL_FILE, "w") as f:
#             f.write(f"{ts}|{_hash(ts)}")

#         logger.info("[trial] file write SUCCESS")

#     except Exception as e:
#         logger.error(f"[trial] file write FAILED: {e}")


# # ==============================
# # CORE CHECK
# # ==============================
# def check_trial():
#     now = time.time()

#     reg_ts, reg_hash = _read_reg()
#     file_ts, file_hash = _read_file()

#     # First run
#     if reg_ts is None and file_ts is None:
#         _write_reg(now)
#         _write_file(now)
#         logger.info("[trial] first run initialized")
#         return

#     # Sync if one missing
#     if reg_ts is None and file_ts is not None:
#         _write_reg(file_ts)
#         reg_ts, reg_hash = _read_reg()

#     if file_ts is None and reg_ts is not None:
#         _write_file(reg_ts)
#         file_ts, file_hash = _read_file()

#     # Integrity check
#     if reg_ts is None or file_ts is None:
#         raise HTTPException(403, "Trial integrity error")

#     if reg_hash != _hash(reg_ts) or file_hash != _hash(file_ts):
#         raise HTTPException(403, "Trial tampering detected")

#     if abs(reg_ts - file_ts) > 5:
#         raise HTTPException(403, "Trial mismatch detected")

#     install_ts = reg_ts

#     elapsed_days = (now - install_ts) / _SECONDS_PER_DAY
#     remaining = _TRIAL_DAYS - elapsed_days

#     if elapsed_days > _TRIAL_DAYS:
#         raise HTTPException(403, "Trial expired")

#     logger.info(f"[trial] {remaining:.1f} days remaining")


# # ==============================
# # WATCHDOG
# # ==============================
# async def trial_watchdog(interval_seconds: float = 60):
#     while True:
#         await asyncio.sleep(interval_seconds)
#         try:
#             check_trial()
#         except Exception as e:
#             logger.error(f"[trial] watchdog: {e}")


# # ==============================
# # FASTAPI INTEGRATION
# # ==============================
# def init_trial(app):

#     @app.on_event("startup")
#     async def startup_event():
#         try:
#             check_trial()
#         except Exception as e:
#             logger.error(f"[trial] startup blocked but server allowed: {e}")

#         asyncio.create_task(trial_watchdog())

#     @app.middleware("http")
#     async def trial_middleware(request, call_next):

#         # allow docs/static
#         if request.url.path.startswith(("/static", "/docs", "/openapi.json")):
#             return await call_next(request)

#         try:
#             check_trial()
#         except HTTPException as e:
#             return JSONResponse(
#                 status_code=e.status_code,
#                 content={"detail": e.detail}
#             )
#         except Exception as e:
#             return JSONResponse(
#                 status_code=500,
#                 content={"detail": "Internal error in trial system"}
#             )

#         return await call_next(request)