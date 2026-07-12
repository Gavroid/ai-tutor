#!/usr/bin/env python3
"""Production WS smoke test через Python client.

Подключается к wss://192.168.1.86/ws/ai/chat?token=<jwt>,
шлёт запрос, проверяет что приходят chunks и done.
"""
import json
import ssl
import sys
import time
import urllib.request

import websocket  # pip install websocket-client


BASE = "https://192.168.1.86"
ctx = ssl._create_unverified_context()


def get_token():
    req = urllib.request.Request(
        f"{BASE}/api/v1/auth/login",
        data=json.dumps({"email": "kirill@example.com", "password": "strongpass1"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.loads(r.read())["access_token"]


def test_chat_ws():
    token = get_token()
    print(f"[1] Got token: {token[:40]}...")

    # WS URL: заменяем https на wss
    ws_url = BASE.replace("https", "wss") + f"/ws/ai/chat?token={token}"
    print(f"[2] Connecting to {ws_url}")

    # Self-signed cert bypass
    ws = websocket.create_connection(
        ws_url, timeout=15, sslopt={"cert_reqs": ssl.CERT_NONE}
    )
    print("[3] WS connected")

    # Отправляем запрос
    payload = {
        "history": [
            {"role": "user", "content": "Привет! Объясни кратко, что такое дробь?"}
        ],
        "topic_id": None,
    }
    ws.send(json.dumps(payload))
    print("[4] Sent payload, waiting for chunks...")

    chunks = []
    done = None
    deadline = time.time() + 60  # 60 сек max

    while time.time() < deadline:
        try:
            ws.settimeout(max(1, deadline - time.time()))
            msg = ws.recv()
        except websocket.WebSocketTimeoutException:
            print(f"[5] Timeout, collected {len(chunks)} chunks, done={done is not None}")
            break

        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            print(f"[!] Non-JSON message: {msg[:100]}")
            continue

        if data.get("type") == "chunk":
            chunks.append(data.get("content", ""))
            print(f"[chunk] {data.get('content', '')[:80]}", end="\r")
        elif data.get("type") == "done":
            done = data
            print(f"\n[done] model={data.get('model')}, tokens={data.get('output_tokens')}")
            break
        elif data.get("type") == "error":
            print(f"\n[!] Error: {data.get('message')}")
            break
        else:
            print(f"\n[?] Unknown type: {data}")

    ws.close()

    # Проверки
    if not chunks:
        print("\n✗ FAIL: no chunks received")
        return 1
    if not done:
        print("\n✗ FAIL: no done received")
        return 1

    full_response = "".join(chunks)
    print(f"\n✓ PASS: {len(chunks)} chunks, {len(full_response)} chars total")
    print(f"  First chunk: {chunks[0][:80]}...")
    print(f"  Last chunk:  {chunks[-1][:80]}...")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(test_chat_ws())
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        sys.exit(2)
