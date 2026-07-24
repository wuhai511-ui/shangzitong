import base64
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from core.config import settings


def _get_key() -> bytes:
    raw = settings.PAYMENT_CREDENTIAL_KEY.encode("utf-8")
    return hashlib.sha256(raw).digest()


def encrypt_field(plaintext: str) -> str:
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("ascii")


def decrypt_field(ciphertext_b64: str) -> str:
    try:
        payload = base64.b64decode(ciphertext_b64)
    except Exception:
        raise ValueError("Invalid ciphertext encoding")
    if len(payload) < 28:
        raise ValueError("Ciphertext too short")
    nonce = payload[:12]
    ciphertext = payload[12:]
    key = _get_key()
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        raise ValueError("Decryption failed: data may be tampered")
    return plaintext.decode("utf-8")


def mask_value(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]
