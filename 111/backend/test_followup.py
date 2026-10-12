import json
import urllib.request

BASE = "http://localhost:8000/api"

# 创建会话
req = urllib.request.Request(
    BASE + "/sessions",
    data=json.dumps({"title": "test"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    sid = json.loads(resp.read())["id"]
    print(f"SID: {sid}")

def stream_chat(question):
    req = urllib.request.Request(
        BASE + "/chat/stream",
        data=json.dumps({"session_id": sid, "question": question}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    events = []
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="ignore").rstrip()
                if line.startswith("event:"):
                    events.append(line[6:].strip())
                elif line.startswith("data:"):
                    try:
                        d = json.loads(line[5:].strip())
                        if d.get("type") == "mode":
                            print(f"  ✓ mode={d['payload']}")
                        if d.get("type") == "error":
                            print(f"  ! error: {d['payload']}")
                    except Exception:
                        pass
    except urllib.error.HTTPError as e:
        print(f"  HTTPError {e.code}")
    return events

print("\n--- Q1: full mode (no followup keywords) ---")
events = stream_chat("Sales last month")
print(f"  events: {events[:8]}")

print("\n--- Q2: followup mode (contains 'again' keyword) ---")
events = stream_chat("filter out vip customer please again")
print(f"  events: {events[:8]}")

print("\n--- Q3: chart_only mode (switch to line chart) ---")
events = stream_chat("change to line chart please")
print(f"  events: {events[:8]}")

print("\nDONE")
