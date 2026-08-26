import os
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn


app = FastAPI()

users = {}
clients = {}


@app.get("/")
async def home():
    return {
        "status": "SecureChat server is running",
        "websocket": "/ws"
    }


async def send_json(websocket, data):
    await websocket.send_text(json.dumps(data))


async def broadcast_user_list():
    packet = {
        "type": "users",
        "users": list(users.keys())
    }

    for websocket in list(clients.values()):
        try:
            await send_json(websocket, packet)
        except Exception:
            pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    username = None

    try:

        while True:

            raw_message = await websocket.receive_text()

            if not raw_message.strip():
                continue

            data = json.loads(raw_message)

            msg_type = data.get("type")

            # ---------------- REGISTER ----------------

            if msg_type == "register":

                requested = data.get("username", "").strip()

                if not requested or len(requested) > 32:

                    await send_json(
                        websocket,
                        {
                            "type": "error",
                            "message": "Invalid username."
                        }
                    )

                    continue

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
                    "ed25519": data["ed25519"]
                }

                clients[username] = websocket

                await send_json(
                    websocket,
                    {
                        "type": "registered",
                        "username": username
                    }
                )

                await broadcast_user_list()


            # ---------------- GET PUBLIC KEY ----------------

            elif msg_type == "get_key":

                target = data.get("target")

                user = users.get(target)

                if user:

                    await send_json(
                        websocket,
                        {
                            "type": "public_key",
                            "username": target,
                            "x25519": user["x25519"],
                            "ed25519": user["ed25519"]
                        }
                    )

                else:

                    await send_json(
                        websocket,
                        {
                            "type": "error",
                            "message": "User not found."
                        }
                    )


            # ---------------- MESSAGE ----------------

            elif msg_type == "message":

                target = data.get("target")

                target_websocket = clients.get(target)

                # Server only forwards encrypted packet.
                # Server cannot decrypt the message.

                if target_websocket:

                    try:

                        await send_json(
                            target_websocket,
                            data
                        )

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


    except (
        WebSocketDisconnect,
        json.JSONDecodeError,
        KeyError
    ) as e:

        print(
            f"Client {username} disconnected/error: {e}"
        )


    finally:

        if username:

            users.pop(username, None)
            clients.pop(username, None)

            await broadcast_user_list()


# ---------------- START SERVER ----------------

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", "10000")
    )

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port
    )
