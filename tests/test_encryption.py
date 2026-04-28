from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from src.utils.encryption import decrypt, encrypt


def _new_key() -> str:
    return Fernet.generate_key().decode()


def test_roundtrip():
    key = _new_key()
    assert decrypt(key, encrypt(key, "secret")) == "secret"


def test_empty_string():
    key = _new_key()
    assert decrypt(key, encrypt(key, "")) == ""


def test_wrong_key_raises():
    key1 = _new_key()
    key2 = _new_key()
    token = encrypt(key1, "data")
    with pytest.raises(Exception):
        decrypt(key2, token)
