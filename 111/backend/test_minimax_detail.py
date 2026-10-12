import json, urllib.request, time

BASE = "http://localhost:8000/api"

# 新会话
req = urllib.request.Request(
    BASE + "/sessions", data=json.dumps({"title": "minimax-detailed"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}, method="POST",
)
with urllib.request.urlopen(req) as resp:
    sid = json.loads(resp.read())["id"]
print(f"SID: {sid}\n")

questions = [
    "show me total sales by region",
    "no wait, only East region",
    "switch to line chart",
]

for i, q in enumerate(questions, 1):
    print(f"\n--- Q{i}: {q!r} ---")
    req = urllib.request.Request(
        BASE + "/chat/stream",
        data=json.dumps({"session_id": sid, "question": q}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="ignore").rstrip()
            if line.startswith("data:"):
                d = json.loads(line[5:].strip())
                t = d.get("type")
                p = d.get("payload")
                if t == "mode":
                    print(f"  [OK] MODE: {p}")
                elif t == "sql":
                    print(f"  [OK] SQL: {p[:140]}")
                elif t == "data":
                    payload = p or {}
                    rows = payload.get("rows") or []
                    print(f"  [OK] ROWS: {payload.get('row_count')} 行, sample={rows[:2]}")
                elif t == "chart":
                    print(f"  [OK] CHART: type={p.get('type')}, x={p.get('x')!r}, y={p.get('y')!r}")
                elif t == "summary":
                    s = (p or {}).get("summary", "")
                    if s.strip(): print(f"  [OK] SUMMARY: {s[:160]}")
                elif t == "error":
                    print(f"  [ERR] ERROR: {p[:200]}")
                elif t == "done":
                    p = p or {}
                    print(f"  --> DONE: elapsed={p.get('elapsed_ms')}ms rounds={p.get('rounds')}")
    print(f"  (total: {time.time()-start:.2f}s)")
