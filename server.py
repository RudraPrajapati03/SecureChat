import os
import asyncio
import json
import websockets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5000"))

users = {}
clients = {}
lock = asyncio.Lock()


async def send_json(websocket, data):
    await websocket.send(json.dumps(data))


async def broadcast_user_list():
    async with lock:
        packet = {"type": "users", "users": list(users.keys())}
        connections = list(clients.values())

    for websocket in connections:
        try:
            await send_json(websocket, packet)
        except Exception:
            pass


async def handle_client(websocket):
    username = None

    try:
        async for raw_message in websocket:
            if not raw_message.strip():
                continue

            data = json.loads(raw_message)
            msg_type = data.get("type")

            if msg_type == "register":
                requested = data.get("username", "").strip()

                if not requested or len(requested) > 32:
                    await send_json(
                        websocket,
                        {"type": "error", "message": "Invalid username."}
                    )
                    continue

                async with lock:
                    if requested in users:
                        await send_json(
                            websocket,
                            {
                                "type": "error",
                                "message": "Username already in use."
                            }
                        )
                        continue

                    username = requested
                    users[username] = {
                        "x25519": data["x25519"],
                        "ed25519": data["ed25519"],
                    }
                    clients[username] = websocket

                await send_json(
                    websocket,
                    {"type": "registered", "username": username}
                )
                await broadcast_user_list()

            elif msg_type == "get_key":
                target = data.get("target")

                async with lock:
                    user = users.get(target)

                if user:
                    await send_json(
                        websocket,
                        {
                            "type": "public_key",
                            "username": target,
                            "x25519": user["x25519"],
                            "ed25519": user["ed25519"],
                        }
                    )
                else:
                    await send_json(
                        websocket,
                        {"type": "error", "message": "User not found."}
                    )

            elif msg_type == "message":
                target = data.get("target")

                async with lock:
                    target_websocket = clients.get(target)

                # The server only forwards the encrypted packet.
                # It does not possess the private keys needed to decrypt it.
                if target_websocket:
                    try:
                        await send_json(target_websocket, data)
                    except Exception:
                        await send_json(
                            websocket,
                            {
                                "type": "error",
                                "message": "Could not deliver message."
                            }
                        )
                else:
                    await send_json(
                        websocket,
                        {
                            "type": "error",
                            "message": "Recipient is offline."
                        }
                    )

    except (websockets.exceptions.ConnectionClosed, OSError, json.JSONDecodeError) as e:
        print(f"Client disconnected/error: {e}")

    finally:
        if username:
            async with lock:
                users.pop(username, None)
                clients.pop(username, None)

            await broadcast_user_list()


async def main():
    print(f"SecureChat WebSocket server running on {HOST}:{PORT}")

    async with websockets.serve(
        handle_client,
        HOST,
        PORT,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
