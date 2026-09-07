import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import socket
import threading
import json

app = FastAPI(title="SecureChat Relay")

users = {}
clients = {}

@app.get("/")
async def health():
    return {"status": "online", "service": "SecureChat Relay"}

async def broadcast_users():
    packet = {"type": "users", "users": list(users.keys())}
    dead = []
    for username, ws in list(clients.items()):
        try:
            await ws.send_json(packet)
        except Exception:
            dead.append(username)
    for username in dead:
        users.pop(username, None)
        clients.pop(username, None)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "register":
                requested = str(data.get("username", "")).strip()

                if not requested or len(requested) > 32:
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid username."}
                    )
                    continue

                if requested in users:
                    await websocket.send_json(
                        {"type": "error", "message": "Username already in use."}
                    )
                    continue

                if not data.get("x25519") or not data.get("ed25519"):
                    await websocket.send_json(
                        {"type": "error", "message": "Public keys are required."}
                    )
                    continue

                username = requested
                users[username] = {
                    "x25519": data["x25519"],
                    "ed25519": data["ed25519"],
                }
                clients[username] = websocket

                await websocket.send_json(
                    {"type": "registered", "username": username}
                )
                await broadcast_users()

            elif msg_type == "get_key":
                target = data.get("target")
                user = users.get(target)

                if user:
                    await websocket.send_json({
                        "type": "public_key",
                        "username": target,
                        "x25519": user["x25519"],
                        "ed25519": user["ed25519"],
                    })
                else:
                    await websocket.send_json(
                        {"type": "error", "message": "User not found."}
                    )

            elif msg_type == "message":
                target = data.get("target")
                target_ws = clients.get(target)

                if target_ws:
                    # Relay only. The server does not decrypt the packet.
                    await target_ws.send_json(data)
                else:
                    await websocket.send_json(
                        {"type": "error", "message": "Recipient is offline."}
                    )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"Client error: {exc}")
    finally:
        if username:
            users.pop(username, None)
            clients.pop(username, None)
            await broadcast_users()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
