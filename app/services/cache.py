import hashlib
import json
import os
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.from_url(os.environ["UPSTASH_REDIS_URL"], decode_responses=True)


def make_cache_key(prefix: str, *parts: str) -> str:
    joined = "|".join(parts)
    digest = hashlib.sha256(joined.encode()).hexdigest()
    return f"{prefix}:{digest}"


def get_cached(key: str) -> Any | None:
    value = redis_client.get(key)
    return json.loads(value) if value is not None else None


def set_cached(key: str, value: Any, ttl_seconds: int) -> None:
    redis_client.set(key, json.dumps(value), ex=ttl_seconds)
