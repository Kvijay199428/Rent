import os
from cryptography.fernet import Fernet

# Use environment variable or fallback to a generated default for dev
# In production, this should be set via environment variable!
PIN_VAULT_KEY_STR = os.environ.get("TENANT_PIN_VAULT_KEY", "UzZ9Uu5iAC5M1VBUBwiOHInTdRrlwmuCY01OQq7ZHCg=")
PIN_VAULT_KEY = PIN_VAULT_KEY_STR.encode("utf-8")

fernet = Fernet(PIN_VAULT_KEY)

def encrypt_admin_view_pin(pin: str) -> str:
    return fernet.encrypt(pin.encode("utf-8")).decode("utf-8")

def decrypt_admin_view_pin(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

