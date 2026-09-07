# SecureChat — Railway Version

Educational end-to-end encrypted chat using Python.

## Features

- X25519 key agreement
- HKDF-SHA256 key derivation
- AES-GCM message encryption
- Ed25519 signatures
- WebSocket relay
- Multiple clients

## Project structure

```text
SecureChat/
├── client.py
├── server.py
├── requirements.txt
└── README.md
```

## Railway deployment

1. Push this folder to a GitHub repository.
2. In Railway, create a new project and deploy the GitHub repository.
3. Railway should install dependencies from `requirements.txt`.
4. Use this start command:

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

5. Generate a public Railway domain.
6. Copy that domain into `client.py`:

```python
SERVER_URL = "wss://YOUR-RAILWAY-DOMAIN.up.railway.app/ws"
```

The `/ws` path is required.

## Local testing

Run:

```bash
python server.py
```

For local testing, temporarily use:

```python
SERVER_URL = "ws://127.0.0.1:8000/ws"
```

Then start the client:

```bash
python client.py
```

Run two clients with different usernames.

## Security note

This is an educational implementation and has not been independently security-audited. Do not use it for high-risk communications.

The relay forwards encrypted packets and does not intentionally decrypt message content. Private keys are generated locally by each client and are not sent to the server.

Never commit private keys, passwords, API keys, tokens, or other secrets to GitHub.
