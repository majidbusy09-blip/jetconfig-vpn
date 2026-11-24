"""Audited Ed25519 verification adapter backed by PyCA cryptography.

Only public-key verification is exposed. No key generation, signing, private-key
loading, provider access, or execution authorization is provided here.
"""
from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class CryptographyEd25519Backend:
    """Verify raw Ed25519 signatures using the pinned PyCA implementation."""

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            return False
        if not isinstance(message, bytes):
            return False
        if not isinstance(signature, bytes) or len(signature) != 64:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        except InvalidSignature:
            return False
        return True
