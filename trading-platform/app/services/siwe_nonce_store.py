# app/services/siwe_nonce_store.py
from __future__ import annotations

import os
import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
TTL = int(os.environ.get("SIWE_NONCE_TTL_SECONDS", "300"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def nonce_key(nonce: str) -> str:
    return f"siwe:nonce:{nonce}"

def put_nonce(nonce: str) -> None:
    # value = "1" just means "exists"
    r.setex(nonce_key(nonce), TTL, "1")

def consume_nonce(nonce: str) -> bool:
    # atomic-ish: get then delete
    key = nonce_key(nonce)
    val = r.get(key)
    if not val:
        return False
    r.delete(key)
    return True
