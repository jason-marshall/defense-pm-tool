"""Encryption utilities for secure token storage.

Provides Fernet-based symmetric encryption for sensitive data like API tokens.
Uses a salt combined with the application secret key to derive encryption keys.

Usage:
    from src.core.encryption import encrypt_token, decrypt_token

    # Encrypt a token before storing in database
    encrypted = encrypt_token("api-token-secret")

    # Decrypt when needed for API calls
    decrypted = decrypt_token(encrypted)
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

import structlog
from cryptography.fernet import Fernet, InvalidToken

logger = structlog.get_logger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption operations."""

    pass


class DecryptionError(EncryptionError):
    """Failed to decrypt data."""

    pass


class InvalidKeyError(EncryptionError):
    """Invalid encryption key."""

    pass


@lru_cache
def _get_fernet() -> Fernet:
    """Get cached Fernet instance with derived key.

    Derives a Fernet-compatible key from the application's SECRET_KEY
    combined with an ENCRYPTION_SALT for additional security.

    Returns:
        Fernet instance for encryption/decryption

    Raises:
        InvalidKeyError: If key derivation fails
    """
    from src.config import settings  # noqa: PLC0415 - lazy import to avoid circular deps

    try:
        # Combine secret key with salt for key derivation
        salt = getattr(settings, "ENCRYPTION_SALT", "defense-pm-tool-salt")
        key_material = f"{settings.SECRET_KEY}{salt}".encode()

        # Derive a 32-byte key using SHA-256
        derived_key = hashlib.sha256(key_material).digest()

        # Fernet requires base64-encoded 32-byte key
        fernet_key = base64.urlsafe_b64encode(derived_key)

        return Fernet(fernet_key)
    except Exception as e:
        logger.error("encryption_key_derivation_failed", error=str(e))
        raise InvalidKeyError(f"Failed to derive encryption key: {e}") from e


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token for secure storage.

    Args:
        plaintext: The token to encrypt

    Returns:
        Base64-encoded encrypted token

    Raises:
        EncryptionError: If encryption fails
    """
    if not plaintext:
        raise EncryptionError("Cannot encrypt empty token")

    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    except InvalidKeyError:
        raise
    except Exception as e:
        logger.error("token_encryption_failed", error=str(e))
        raise EncryptionError(f"Failed to encrypt token: {e}") from e


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token.

    Args:
        encrypted: Base64-encoded encrypted token

    Returns:
        Decrypted plaintext token

    Raises:
        DecryptionError: If decryption fails (invalid token or key)
    """
    if not encrypted:
        raise DecryptionError("Cannot decrypt empty token")

    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        logger.warning("token_decryption_invalid_token")
        raise DecryptionError("Invalid encrypted token or key mismatch") from None
    except InvalidKeyError:
        raise DecryptionError("Invalid encryption key") from None
    except Exception as e:
        logger.error("token_decryption_failed", error=str(e))
        raise DecryptionError(f"Failed to decrypt token: {e}") from e


def rotate_encryption_key(
    encrypted_tokens: list[str],
    old_secret_key: str,
    old_salt: str,
    new_secret_key: str,
    new_salt: str,
) -> list[str]:
    """Re-encrypt tokens with a new key.

    Use this when rotating encryption keys. Decrypts tokens with the old
    key and re-encrypts with the new key.

    Args:
        encrypted_tokens: List of encrypted tokens to rotate
        old_secret_key: Previous SECRET_KEY
        old_salt: Previous ENCRYPTION_SALT
        new_secret_key: New SECRET_KEY
        new_salt: New ENCRYPTION_SALT

    Returns:
        List of tokens encrypted with the new key

    Raises:
        EncryptionError: If rotation fails
    """
    # Create old Fernet
    old_key_material = f"{old_secret_key}{old_salt}".encode()
    old_derived_key = hashlib.sha256(old_key_material).digest()
    old_fernet = Fernet(base64.urlsafe_b64encode(old_derived_key))

    # Create new Fernet
    new_key_material = f"{new_secret_key}{new_salt}".encode()
    new_derived_key = hashlib.sha256(new_key_material).digest()
    new_fernet = Fernet(base64.urlsafe_b64encode(new_derived_key))

    rotated = []
    for i, encrypted in enumerate(encrypted_tokens):
        try:
            # Decrypt with old key
            decrypted = old_fernet.decrypt(encrypted.encode()).decode()
            # Re-encrypt with new key
            re_encrypted = new_fernet.encrypt(decrypted.encode()).decode()
            rotated.append(re_encrypted)
        except Exception as e:
            raise EncryptionError(f"Failed to rotate token at index {i}: {e}") from e

    logger.info("encryption_key_rotated", token_count=len(rotated))
    return rotated


def clear_encryption_cache() -> None:
    """Clear the cached Fernet instance.

    Call this after changing SECRET_KEY or ENCRYPTION_SALT to force
    re-derivation of the encryption key.
    """
    _get_fernet.cache_clear()
    logger.info("encryption_cache_cleared")
