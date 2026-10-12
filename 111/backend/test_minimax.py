import json, urllib.request

BASE = "http://localhost:8000/api"

# 创建会话
req = urllib.request.Request(
    BASE + "/sessions",
    data=json.dumps({"title": "minimax-test"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    sid = json.loads(resp.read())["id"]
print(f"SID: {sid}")

# 真实提问：让 minimax 走 LangChain SQL Agent 流
req = urllib.request.Request(
    BASE + "/chat/stream",
    data=json.dumps({"session_id": sid, "question": "show me total sales by region"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print("--- 真实 chat 走 minimax ---")
events = []
import time
start = time.time()
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="ignore").rstrip()
            if line.startswith("event:"):
                events.append(line[6:].strip())
            elif line.startswith("data:"):
                try:
                    d = json.loads(line[5:].strip())
                    if d.get("type") == "mode":
                        print(f"  ✓ mode: {d['payload']}")
                    elif d.get("type") == "chart":
                        print(f"  ✓ chart: {d['payload']}")
                    elif d.get("type") == "data":
                        payload = d.get("payload") or {}
                        print(f"  ✓ rows: {payload.get('row_count')}")
                    elif d.get("type") == "error":
                        print(f"  ! error: {d['payload'][:200]}")
                    elif d.get("type") == "summary":
                        s = (d.get("payload") or {}).get("summary", "")
                        if s: print(f"  ✓ summary: {s[:120]}")
                except Exception:
                    pass
except Exception as e:
    print(f"  Exception: {type(e).__name__}: {e}")

print(f"--- elapsed: {time.time()-start:.1f}s, events: {events[:8]}")
