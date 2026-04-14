import time

sap_sessions = {}

SESSION_TIMEOUT = 1500  # 25 minutes


def get_session(key="default"):

    session = sap_sessions.get(key)

    if not session:
        return None

    # check expiry
    if time.time() - session["timestamp"] > SESSION_TIMEOUT:
        sap_sessions.pop(key, None)
        return None

    return session


def set_session(cookies, key="default"):

    sap_sessions[key] = {
        "cookies": cookies,
        "timestamp": time.time()
    }