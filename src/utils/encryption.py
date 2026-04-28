from __future__ import annotations

from cryptography.fernet import Fernet


def encrypt(master_key: str, plaintext: str) -> str:
    return Fernet(master_key.encode()).encrypt(plaintext.encode()).decode()


def decrypt(master_key: str, token: str) -> str:
    return Fernet(master_key.encode()).decrypt(token.encode()).decode()
