import os
import requests

API_KEY = os.getenv("API_KEY", "dev-key")
BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

payloads = [
    {
        "task_type": "cpu_burn",
        "payload": {"milliseconds": 120},
        "idempotency_key": "demo-1",
    },
    {
        "task_type": "data_transform",
        "payload": {
            "data": {"a": 1, "b": 2},
            "select": ["b"],
            "rename": {"b": "beta"},
        },
    },
    {
        "task_type": "http_fetch",
        "payload": {
            "url": "https://example.com",
            "timeout_seconds": 5,
        },
    },
]

for p in payloads:
    r = requests.post(f"{BASE}/v1/tasks", json=p, headers=headers, timeout=10)
    try:
        print(r.status_code, r.json())
    except Exception:
        print(r.status_code, r.text)