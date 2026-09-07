import os
import json
import base64
import hashlib
import threading
import tkinter as tk

from tkinter import messagebox, scrolledtext
import websocket

from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# Railway will provide the public HTTPS domain.
# Replace YOUR-RAILWAY-DOMAIN with your actual Railway domain.
SERVER_URL = "wss://securechat-e8uw.onrender.com/ws"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def raw_public_bytes(public_key) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


class SecureChat:
    def __init__(self, root):
        self.root = root
        self.root.title("SecureChat — E2E Encrypted")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        self.socket = None
        self.username = None
        self.current_user = None

        self.x_private = x25519.X25519PrivateKey.generate()
        self.x_public = self.x_private.public_key()

        self.sign_private = ed25519.Ed25519PrivateKey.generate()
        self.sign_public = self.sign_private.public_key()

        self.user_keys = {}
        self.pending_message = None

        self.create_gui()

    def create_gui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=10)

        tk.Label(top, text="Username:").pack(side="left")
        self.username_entry = tk.Entry(top, width=20)
        self.username_entry.pack(side="left", padx=6)

        tk.Button(top, text="Connect", command=self.connect).pack(side="left")

        self.status = tk.Label(top, text="Disconnected", fg="red")
        self.status.pack(side="left", padx=15)

        user_frame = tk.Frame(self.root)
        user_frame.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(user_frame, text="Chat with:").pack(side="left")
        self.user_entry = tk.Entry(user_frame, width=20)
        self.user_entry.pack(side="left", padx=6)

        tk.Button(
            user_frame, text="Select User", command=self.set_user
        ).pack(side="left")

        self.selected_label = tk.Label(
            user_frame, text="No recipient selected"
        )
        self.selected_label.pack(side="left", padx=15)

        self.chat = scrolledtext.ScrolledText(
            self.root,
            state="disabled",
            wrap=tk.WORD,
            font=("Segoe UI", 10),
        )
        self.chat.pack(fill="both", expand=True, padx=12, pady=8)

        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=12)

        self.message_entry = tk.Entry(bottom, font=("Segoe UI", 10))
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind(
            "<Return>", lambda _event: self.send_message()
        )

        tk.Button(
            bottom, text="Send", width=10, command=self.send_message
        ).pack(side="right", padx=(8, 0))

        security = tk.Label(
            self.root,
            text="E2E design: encryption/decryption happens on the endpoints.",
            anchor="w",
        )
        security.pack(fill="x", padx=12, pady=(0, 8))

    def connect(self):
        if self.socket:
            return

        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Enter a username.")
            return

        try:
            self.socket = websocket.create_connection(
                SERVER_URL,
                timeout=10,
            )

            self.username = username

            self.send_json({
                "type": "register",
                "username": username,
                "x25519": b64(raw_public_bytes(self.x_public)),
                "ed25519": b64(raw_public_bytes(self.sign_public)),
            })

            threading.Thread(
                target=self.receive_loop,
                daemon=True,
            ).start()

            self.status.config(text="Connected", fg="green")
            self.add_chat("[System] Connected to relay server.")

        except Exception as e:
            self.socket = None
            messagebox.showerror("Connection Error", str(e))

    def send_json(self, data):
        if not self.socket:
            return

        try:
            self.socket.send(json.dumps(data))
        except Exception as e:
            self.add_chat(f"[Network] Send failed: {e}")

    def receive_loop(self):
        try:
            while True:
                raw = self.socket.recv()

                if raw is None:
                    break

                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

                if raw.strip():
                    self.process_message(json.loads(raw))

        except Exception as e:
            self.add_chat(f"[Network] Connection closed: {e}")
        finally:
            self.socket = None
            self.root.after(
                0, lambda: self.status.config(
                    text="Disconnected", fg="red"
                )
            )

    def process_message(self, data):
        msg_type = data.get("type")

        if msg_type == "registered":
            self.add_chat(
                f"[System] Logged in as {data['username']}."
            )

        elif msg_type == "users":
            online = [
                u for u in data["users"]
                if u != self.username
            ]
            self.add_chat(
                "[Online] "
                + (", ".join(online) if online else "No other users online.")
            )

        elif msg_type == "public_key":
            username = data["username"]

            self.user_keys[username] = {
                "x25519": data["x25519"],
                "ed25519": data["ed25519"],
            }

            fp = self.fingerprint(unb64(data["ed25519"]))

            self.add_chat(
                f"[Security] {username} public-key fingerprint:\n"
                f"{fp}\n"
                "Verify this fingerprint through a trusted channel "
                "before trusting the contact."
            )

            if self.pending_message and self.current_user == username:
                text = self.pending_message
                self.pending_message = None
                self.finish_send(text)

        elif msg_type == "message":
            self.decrypt_message(data)

        elif msg_type == "error":
            self.add_chat(
                "[Server] " + data.get("message", "Unknown error.")
            )

    def set_user(self):
        username = self.user_entry.get().strip()

        if not username:
            return

        self.current_user = username
        self.selected_label.config(
            text=f"Recipient: {username}"
        )
        self.add_chat(f"[System] Selected {username}.")

        if username not in self.user_keys:
            self.send_json({
                "type": "get_key",
                "target": username,
            })

    def derive_key(self, shared_secret: bytes) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"SecureChat-v1",
        ).derive(shared_secret)

    def encrypt_message(self, plaintext: str, target_key: str):
        receiver_public = (
            x25519.X25519PublicKey.from_public_bytes(
                unb64(target_key)
            )
        )

        ephemeral_private = (
            x25519.X25519PrivateKey.generate()
        )
        ephemeral_public = ephemeral_private.public_key()

        shared_secret = ephemeral_private.exchange(
            receiver_public
        )
        aes_key = self.derive_key(shared_secret)

        nonce = os.urandom(12)

        ciphertext = AESGCM(aes_key).encrypt(
            nonce,
            plaintext.encode("utf-8"),
            None,
        )

        signed_data = (
            raw_public_bytes(ephemeral_public)
            + nonce
            + ciphertext
        )

        signature = self.sign_private.sign(signed_data)

        return {
            "ephemeral": b64(
                raw_public_bytes(ephemeral_public)
            ),
            "nonce": b64(nonce),
            "ciphertext": b64(ciphertext),
            "signature": b64(signature),
        }

    def decrypt_message(self, data):
        sender = data.get("sender")

        if sender not in self.user_keys:
            self.send_json({
                "type": "get_key",
                "target": sender,
            })
            self.add_chat(
                f"[Security] Fetching {sender}'s public key..."
            )
            self.root.after(
                500,
                lambda d=data: self.decrypt_message(d),
            )
            return

        try:
            ephemeral_bytes = unb64(data["ephemeral"])
            nonce = unb64(data["nonce"])
            ciphertext = unb64(data["ciphertext"])
            signature = unb64(data["signature"])

            signing_data = (
                ephemeral_bytes + nonce + ciphertext
            )

            sender_sign_public = (
                ed25519.Ed25519PublicKey.from_public_bytes(
                    unb64(
                        self.user_keys[sender]["ed25519"]
                    )
                )
            )

            sender_sign_public.verify(
                signature,
                signing_data,
            )

            ephemeral_public = (
                x25519.X25519PublicKey.from_public_bytes(
                    ephemeral_bytes
                )
            )

            shared_secret = self.x_private.exchange(
                ephemeral_public
            )
            aes_key = self.derive_key(shared_secret)

            plaintext = AESGCM(aes_key).decrypt(
                nonce,
                ciphertext,
                None,
            ).decode("utf-8")

            self.add_chat(
                f"{sender}: {plaintext}"
            )

        except Exception as e:
            self.add_chat(
                "[Security] Message rejected: "
                "authentication/decryption failed."
            )
            print("Decryption error:", e)

    def send_message(self):
        if not self.socket:
            messagebox.showerror(
                "Error", "Connect first."
            )
            return

        if not self.current_user:
            messagebox.showerror(
                "Error",
                "Select a recipient first.",
            )
            return

        text = self.message_entry.get().strip()

        if not text:
            return

        if self.current_user not in self.user_keys:
            self.pending_message = text
            self.send_json({
                "type": "get_key",
                "target": self.current_user,
            })
            self.add_chat(
                "[Security] Fetching recipient public key..."
            )
            return

        self.finish_send(text)

    def finish_send(self, text):
        info = self.user_keys.get(self.current_user)

        if not info:
            self.add_chat(
                "[Security] Recipient public key unavailable."
            )
            return

        encrypted = self.encrypt_message(
            text,
            info["x25519"],
        )

        self.send_json({
            "type": "message",
            "sender": self.username,
            "target": self.current_user,
            **encrypted,
        })

        self.add_chat(f"You: {text}")

        self.add_chat(
            "🔐 ENCRYPTED PACKET\n"
            f"Ciphertext: {encrypted['ciphertext']}\n"
            f"Nonce: {encrypted['nonce']}\n"
            f"Signature: {encrypted['signature']}"
        )

        self.message_entry.delete(0, tk.END)

    @staticmethod
    def fingerprint(public_key: bytes) -> str:
        digest = hashlib.sha256(public_key).hexdigest().upper()
        return " ".join(
            digest[i:i + 4]
            for i in range(0, len(digest), 4)
        )

    def add_chat(self, message):
        def update():
            self.chat.config(state="normal")
            self.chat.insert(
                tk.END,
                message + "\n\n",
            )
            self.chat.config(state="disabled")
            self.chat.see(tk.END)

        self.root.after(0, update)


if __name__ == "__main__":
    root = tk.Tk()
    app = SecureChat(root)
    root.mainloop()
