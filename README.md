# 🔐 SecureChat

A simple **End-to-End Encrypted (E2E) Chat Application** built with Python.

SecureChat lets multiple clients communicate through a central WebSocket relay server. The server forwards encrypted message packets and does not have the private keys required to decrypt message content.

## ✨ Features

- 🔒 End-to-End encrypted messaging
- 🌐 Internet communication using WebSockets
- 👥 Multiple connected users
- 🔑 X25519 key exchange
- ✍️ Ed25519 digital signatures
- 🛡️ AES-GCM authenticated encryption
- ☁️ Render deployment support
- 💻 Clients can run on different PCs and networks

## 🏗️ Architecture

```text
             Internet
                 │
                 ▼
       ┌───────────────────┐
       │   Render Server   │
       │  SecureChat Relay │
       │   WebSocket /ws   │
       └─────────┬─────────┘
                 │
          ┌──────┴──────┐
          ▼             ▼
     ┌─────────┐   ┌─────────┐
     │ Client 1│   │ Client 2│
     │   PC 1  │   │   PC 2  │
     └─────────┘   └─────────┘
```

The server handles user registration, public-key exchange, online-user information, and encrypted-packet forwarding. It does not decrypt message content.

## 🔐 Security Design

### X25519
Used to establish a shared secret between sender and receiver.

### HKDF-SHA256
Derives a 32-byte AES key from the shared secret.

### AES-GCM
Encrypts and authenticates message content.

### Ed25519
Signs encrypted message packets so the receiver can verify the sender.

### Message Flow

```text
Sender
  │
  ├── Generate ephemeral X25519 key
  ├── Derive shared secret
  ├── Derive AES key using HKDF-SHA256
  ├── Encrypt with AES-GCM
  ├── Sign packet with Ed25519
  ▼
Render Server
  │
  └── Forwards encrypted packet
  ▼
Receiver
  │
  ├── Verify Ed25519 signature
  ├── Derive shared secret
  ├── Derive AES key
  └── Decrypt with AES-GCM
```

## 📁 Project Structure

```text
SecureChat/
├── client.py
├── server.py
├── requirements.txt
└── README.md
```

## ⚙️ Requirements

- Python 3.9+
- Internet connection
- Git
- Render account for public server deployment

## 💻 Client Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install client dependencies directly:

```bash
pip install websocket-client cryptography
```

## 🌐 Render Deployment

Create a **Web Service** from the GitHub repository.

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

The WebSocket endpoint is:

```text
/ws
```

The client should use:

```python
SERVER_URL = "wss://YOUR-RENDER-DOMAIN.onrender.com/ws"
```

Example:

```python
SERVER_URL = "wss://securechat-e0uw.onrender.com/ws"
```

## 🖥️ Running the Client

```bash
python client.py
```

Enter a unique username and click **Connect**.

To start a chat:

1. Connect to the server.
2. Enter the other user's username.
3. Select the user.
4. Type a message.
5. Press **Send**.

## 🌍 Using Two PCs

Both PCs only need `client.py`.

```text
PC 1                         PC 2
client.py                    client.py
   │                            │
   └────────── Internet ────────┘
                 │
                 ▼
          Render WebSocket
              Server
```

The PCs do **not** need to be on the same Wi-Fi network.

When using the deployed Render server, do not run `server.py` on the client PCs.

## 🧪 Local Testing

Start the local server:

```bash
python server.py
```

For local testing, use:

```python
SERVER_URL = "ws://127.0.0.1:10000/ws"
```

For Render, change it back to:

```python
SERVER_URL = "wss://YOUR-RENDER-DOMAIN.onrender.com/ws"
```

## 📦 requirements.txt

```text
fastapi
uvicorn[standard]
websocket-client
cryptography
```

## ⚠️ Notes

- Render's free instance can spin down after inactivity, so the first connection after inactivity may be slower.
- Usernames must be unique while connected.
- The server is designed as an encrypted-packet relay and does not receive the plaintext message.
- This project has not been independently security-audited and should be treated as an educational implementation.
- Never commit private keys, passwords, API keys, or other secrets to GitHub.

## 🛠️ Troubleshooting

### 404 / Connection Error

Make sure the client URL includes `/ws`:

```python
SERVER_URL = "wss://YOUR-RENDER-DOMAIN.onrender.com/ws"
```

### Render deployment error

Verify:

```text
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn server:app --host 0.0.0.0 --port $PORT
```

Also verify that `requirements.txt` contains:

```text
fastapi
uvicorn[standard]
websocket-client
cryptography
```

## 📜 License

This project is for educational and development purposes. Add a license appropriate to your intended distribution before publishing the project.
