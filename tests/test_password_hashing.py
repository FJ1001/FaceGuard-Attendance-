"""Tests for bcrypt + legacy SHA-256 password verification."""

import hashlib

from auth.password_hashing import SALT, hash_password, verify_password, is_legacy_sha256_hash


def test_bcrypt_roundtrip():
    h = hash_password("secret-password-1")
    assert verify_password("secret-password-1", h)
    assert not verify_password("wrong", h)


def test_legacy_sha256_verify():
    legacy = hashlib.sha256(("mypass" + SALT).encode()).hexdigest()
    assert verify_password("mypass", legacy)
    assert is_legacy_sha256_hash(legacy)
    assert not is_legacy_sha256_hash(hash_password("x"))


def test_reject_empty():
    assert not verify_password("", hash_password("a"))
    assert not verify_password("a", "")
