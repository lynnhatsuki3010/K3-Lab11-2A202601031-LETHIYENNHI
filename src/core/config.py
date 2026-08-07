"""
Lab 11 — Configuration & API Key Setup
"""
import os

# Multiple Gemini keys so a quota-exhausted key can be swapped for a backup
# one without stopping the run. Configure via .env as either:
#   GOOGLE_API_KEY_POOL=key1,key2,key3
# or numbered vars: GOOGLE_API_KEY, GOOGLE_API_KEY_2, GOOGLE_API_KEY_3, ...
_key_pool: list[str] = []
_key_index: int = 0


def _collect_key_pool() -> list[str]:
    pool_env = os.environ.get("GOOGLE_API_KEY_POOL", "")
    keys = [k.strip() for k in pool_env.split(",") if k.strip()]

    if not keys:
        i = 1
        while True:
            name = "GOOGLE_API_KEY" if i == 1 else f"GOOGLE_API_KEY_{i}"
            val = os.environ.get(name, "").strip()
            if not val:
                break
            keys.append(val)
            i += 1

    seen: set[str] = set()
    unique = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def setup_api_key():
    """Load Google API key(s) from environment (.env) or prompt.

    Also builds the rotation pool (see _collect_key_pool) so
    rotate_google_api_key() has backup keys to switch to on quota errors.
    """
    global _key_pool, _key_index
    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = input("Enter Google API Key: ")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"

    _key_pool = _collect_key_pool()
    _key_index = 0
    if _key_pool:
        os.environ["GOOGLE_API_KEY"] = _key_pool[0]

    n = len(_key_pool) or 1
    print(f"API key loaded ({n} Gemini key{'s' if n != 1 else ''} available).")


def rotate_google_api_key() -> str | None:
    """Switch GOOGLE_API_KEY to the next key in the pool.

    Call this when a call fails with a quota/429 error, THEN rebuild any
    agent/runner that was already constructed — google-adk caches its genai
    Client (and therefore the key) on first use per agent instance, so
    rotating the env var alone does not affect agents built before the
    rotation.

    Returns the new key, or None if there is no backup key left to try.
    """
    global _key_index
    if not _key_pool or _key_index + 1 >= len(_key_pool):
        return None
    _key_index += 1
    next_key = _key_pool[_key_index]
    os.environ["GOOGLE_API_KEY"] = next_key
    print(f"Quota hit — rotating to backup Gemini API key #{_key_index + 1}/{len(_key_pool)}")
    return next_key


# Allowed banking topics (used by topic_filter)
ALLOWED_TOPICS = [
    "banking", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit",
    "deposit", "withdrawal", "balance", "payment",
    "tai khoan", "giao dich", "tiet kiem", "lai suat",
    "chuyen tien", "the tin dung", "so du", "vay",
    "ngan hang", "atm",
]

# Blocked topics (immediate reject)
BLOCKED_TOPICS = [
    "hack", "exploit", "weapon", "drug", "illegal",
    "violence", "gambling", "bomb", "kill", "steal",
]
