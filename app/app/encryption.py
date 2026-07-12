"""
app/encryption.py
Hybrid AES-256-GCM + RSA-OAEP encryption for secure login payloads.
"""

import os
import base64
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

RSA_KEY_PATH = os.environ.get("RSA_KEY_PATH", "./keys")
PRIVATE_KEY_FILE = os.path.join(RSA_KEY_PATH, "private.pem")
PUBLIC_KEY_FILE = os.path.join(RSA_KEY_PATH, "public.pem")


def ensure_keys():
    """Generate RSA key pair if not exists."""
    os.makedirs(RSA_KEY_PATH, exist_ok=True)
    if not os.path.exists(PRIVATE_KEY_FILE):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        # Save private key
        with open(PRIVATE_KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        # Save public key
        public_key = private_key.public_key()
        with open(PUBLIC_KEY_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        print(f"[encryption] Generated new RSA key pair in {RSA_KEY_PATH}")


def get_public_key_pem() -> str:
    """Return the RSA public key in PEM format."""
    ensure_keys()
    with open(PUBLIC_KEY_FILE, "r") as f:
        return f.read()


def decrypt_payload(encrypted_aes_key_b64: str, encrypted_data_b64: str, nonce_b64: str) -> dict:
    """Decrypt hybrid-encrypted payload (RSA-encrypted AES key + AES-GCM encrypted data)."""
    ensure_keys()

    # Load private key
    with open(PRIVATE_KEY_FILE, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

    # Decode base64
    encrypted_aes_key = base64.b64decode(encrypted_aes_key_b64)
    encrypted_data = base64.b64decode(encrypted_data_b64)
    nonce = base64.b64decode(nonce_b64)

    # Decrypt AES key with RSA-OAEP
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Decrypt data with AES-GCM
    aesgcm = AESGCM(aes_key)
    decrypted_bytes = aesgcm.decrypt(nonce, encrypted_data, None)

    return json.loads(decrypted_bytes.decode("utf-8"))

