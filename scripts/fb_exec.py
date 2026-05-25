import os
#!/usr/bin/env python3
"""Filebrowser remote shell exec via WebSocket."""

import asyncio, json, sys, urllib.request
import websockets

HOST = os.environ.get("R36S_HOST", "192.168.4.1")
USER = "ark"
PASS = "ark"


def login():
    req = urllib.request.Request(
        f"http://{HOST}/api/login",
        data=json.dumps({"username": USER, "password": PASS}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req).read().decode()


def patch_user_commands(token, commands):
    user = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(f"http://{HOST}/api/users/1", headers={"X-Auth": token})
        ).read()
    )
    user["commands"] = commands
    body = json.dumps({"what": "user", "which": ["commands"], "data": user}).encode()
    req = urllib.request.Request(
        f"http://{HOST}/api/users/1",
        data=body,
        headers={"X-Auth": token, "Content-Type": "application/json"},
        method="PUT",
    )
    return urllib.request.urlopen(req).status


async def run(cmd, path="/"):
    token = login()
    leading = cmd.split()[0]
    patch_user_commands(token, [leading])
    uri = f"ws://{HOST}/api/command/{path.lstrip('/')}?auth={token}"
    async with websockets.connect(uri) as ws:
        await ws.send(cmd)  # raw text, not JSON
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=15)
                print(msg, end="", flush=True)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            pass
        print()


if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]) or "echo hello"
    asyncio.run(run(cmd))
