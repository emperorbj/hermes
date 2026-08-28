from app.services.cache import get_cached, make_cache_key, set_cached

key = make_cache_key("test", "hello", "world")

print("Before set:", get_cached(key))
set_cached(key, {"message": "it works"}, ttl_seconds=60)
print("After set:", get_cached(key))
