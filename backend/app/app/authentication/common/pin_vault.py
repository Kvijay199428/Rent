import os
from cryptography.fernet import Fernet


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} environment variable is required and must not be empty. "
            "Refusing to start with a fallback/guessable vault key."
        )
    return value


# No hardcoded fallback: the Fernet key MUST come from the environment so a
# leaked database (e.g. a backup) cannot be decrypted with a public constant.
PIN_VAULT_KEY_STR = _require_env("tenantPin_VAULT_KEY")
try:
    PIN_VAULT_KEY = PIN_VAULT_KEY_STR.encode("utf-8")
    fernet = Fernet(PIN_VAULT_KEY)
except Exception as exc:
    raise RuntimeError(
        "tenantPin_VAULT_KEY is not a valid Fernet key "
        "(expected urlsafe base64 of exactly 32 bytes). Refusing to start."
    ) from exc


def encrypt_admin_view_pin(pin: str) -> str:
    return fernet.encrypt(pin.encode("utf-8")).decode("utf-8")


def decrypt_admin_view_pin(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
