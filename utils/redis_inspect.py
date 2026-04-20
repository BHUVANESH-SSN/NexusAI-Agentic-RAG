import redis
import json
import sys

def inspect_redis():
    r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    print("--- REDIS INSPECTOR ---")
    try:
        r.ping()
        print("Connected to Redis at 127.0.0.1:6379")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    keys = r.keys("chat_history:*")
    if not keys:
        print("No chat_history keys found.")
        return

    print(f"Found {len(keys)} history keys:")
    for key in keys:
        msgs = r.lrange(key, 0, -1)
        ttl = r.ttl(key)
        print(f"\nKey: {key} (TTL: {ttl}s)")
        for m in msgs:
            try:
                data = json.loads(m)
                role = "User" if data.get("type") == "human" else "Assistant"
                contentSnippet = data.get("content", "")[:50] + "..."
                print(f"  [{role}] {contentSnippet}")
            except:
                print(f"  [RAW] {m}")

if __name__ == "__main__":
    inspect_redis()
