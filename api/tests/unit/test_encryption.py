"""Unit tests for encryption utilities.

Tests the Fernet-based token encryption and decryption functions.
"""

from unittest.mock import patch

import pytest

from src.core.encryption import (
    DecryptionError,
    EncryptionError,
    InvalidKeyError,
    clear_encryption_cache,
    decrypt_token,
    encrypt_token,
    rotate_encryption_key,
)


class TestEncryptionExceptions:
    """Tests for encryption exception hierarchy."""

    def test_encryption_error_base(self):
        """EncryptionError should be base exception."""
        error = EncryptionError("Test error")
        assert str(error) == "Test error"

    def test_decryption_error_inherits(self):
        """DecryptionError should inherit from EncryptionError."""
        error = DecryptionError("Decryption failed")
        assert isinstance(error, EncryptionError)

    def test_invalid_key_error_inherits(self):
        """InvalidKeyError should inherit from EncryptionError."""
        error = InvalidKeyError("Bad key")
        assert isinstance(error, EncryptionError)


class TestEncryptToken:
    """Tests for encrypt_token function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_encryption_cache()

    def test_encrypt_token_success(self):
        """Should encrypt a token successfully."""
        plaintext = "my-secret-api-token"
        encrypted = encrypt_token(plaintext)

        assert encrypted != plaintext
        assert len(encrypted) > len(plaintext)
        # Fernet tokens are base64-encoded
        assert encrypted.replace("=", "").isalnum() or "-" in encrypted or "_" in encrypted

    def test_encrypt_token_empty(self):
        """Should raise error for empty token."""
        with pytest.raises(EncryptionError) as exc:
            encrypt_token("")
        assert "Cannot encrypt empty token" in str(exc.value)

    def test_encrypt_produces_different_output(self):
        """Each encryption should produce different ciphertext (due to IV)."""
        plaintext = "my-secret-token"
        encrypted1 = encrypt_token(plaintext)
        encrypted2 = encrypt_token(plaintext)

        # Fernet uses random IV, so same plaintext produces different ciphertext
        assert encrypted1 != encrypted2

    def test_encrypt_special_characters(self):
        """Should handle tokens with special characters."""
        plaintext = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt_token(plaintext)
        assert encrypted != plaintext

    def test_encrypt_unicode(self):
        """Should handle unicode characters."""
        plaintext = "token-with-emoji-\U0001f512-and-chars-äöü"
        encrypted = encrypt_token(plaintext)
        assert encrypted != plaintext

    def test_encrypt_long_token(self):
        """Should handle long tokens."""
        plaintext = "x" * 10000
        encrypted = encrypt_token(plaintext)
        assert len(encrypted) > len(plaintext)


class TestDecryptToken:
    """Tests for decrypt_token function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_encryption_cache()

    def test_decrypt_token_success(self):
        """Should decrypt an encrypted token."""
        plaintext = "my-secret-api-token"
        encrypted = encrypt_token(plaintext)
        decrypted = decrypt_token(encrypted)

        assert decrypted == plaintext

    def test_decrypt_token_empty(self):
        """Should raise error for empty token."""
        with pytest.raises(DecryptionError) as exc:
            decrypt_token("")
        assert "Cannot decrypt empty token" in str(exc.value)

    def test_decrypt_invalid_token(self):
        """Should raise error for invalid token."""
        with pytest.raises(DecryptionError) as exc:
            decrypt_token("not-a-valid-encrypted-token")
        assert "Invalid encrypted token" in str(exc.value)

    def test_decrypt_tampered_token(self):
        """Should raise error for tampered token."""
        encrypted = encrypt_token("secret")
        # Tamper with the encrypted data
        tampered = encrypted[:-5] + "xxxxx"

        with pytest.raises(DecryptionError):
            decrypt_token(tampered)

    def test_decrypt_special_characters(self):
        """Should preserve special characters through round-trip."""
        plaintext = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encrypt_token(plaintext)
        decrypted = decrypt_token(encrypted)
        assert decrypted == plaintext

    def test_decrypt_unicode(self):
        """Should preserve unicode through round-trip."""
        plaintext = "token-with-emoji-\U0001f512-and-chars-äöü"
        encrypted = encrypt_token(plaintext)
        decrypted = decrypt_token(encrypted)
        assert decrypted == plaintext


class TestEncryptionRoundTrip:
    """Tests for encrypt/decrypt round-trip."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_encryption_cache()

    def test_round_trip_multiple_tokens(self):
        """Should handle multiple tokens correctly."""
        tokens = [
            "token-1-simple",
            "token-2-with-special-chars!@#$",
            "token-3-unicode-äöü",
            "token-4-long-" + "x" * 1000,
        ]

        encrypted = [encrypt_token(t) for t in tokens]
        decrypted = [decrypt_token(e) for e in encrypted]

        assert decrypted == tokens

    def test_round_trip_preserves_whitespace(self):
        """Should preserve whitespace in tokens."""
        plaintext = "  token  with  spaces  "
        encrypted = encrypt_token(plaintext)
        decrypted = decrypt_token(encrypted)
        assert decrypted == plaintext

    def test_round_trip_newlines(self):
        """Should preserve newlines in tokens."""
        plaintext = "token\nwith\nnewlines"
        encrypted = encrypt_token(plaintext)
        decrypted = decrypt_token(encrypted)
        assert decrypted == plaintext


class TestKeyRotation:
    """Tests for encryption key rotation."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_encryption_cache()

    def test_rotate_encryption_key(self):
        """Should re-encrypt tokens with new key."""
        # Create tokens with old key
        old_secret = "old-secret-key-32-chars-minimum!"
        old_salt = "old-salt"
        new_secret = "new-secret-key-32-chars-minimum!"
        new_salt = "new-salt"

        # Manually encrypt with old key
        import base64
        import hashlib

        from cryptography.fernet import Fernet

        old_material = f"{old_secret}{old_salt}".encode()
        old_derived = hashlib.sha256(old_material).digest()
        old_fernet = Fernet(base64.urlsafe_b64encode(old_derived))

        plaintexts = ["token1", "token2", "token3"]
        old_encrypted = [old_fernet.encrypt(p.encode()).decode() for p in plaintexts]

        # Rotate to new key
        new_encrypted = rotate_encryption_key(
            old_encrypted, old_secret, old_salt, new_secret, new_salt
        )

        # Verify new encrypted tokens are different
        assert new_encrypted != old_encrypted

        # Verify can decrypt with new key
        new_material = f"{new_secret}{new_salt}".encode()
        new_derived = hashlib.sha256(new_material).digest()
        new_fernet = Fernet(base64.urlsafe_b64encode(new_derived))

        decrypted = [new_fernet.decrypt(e.encode()).decode() for e in new_encrypted]
        assert decrypted == plaintexts

    def test_rotate_empty_list(self):
        """Should handle empty token list."""
        result = rotate_encryption_key(
            [],
            "old-secret-key-32-chars-minimum!",
            "old-salt",
            "new-secret-key-32-chars-minimum!",
            "new-salt",
        )
        assert result == []

    def test_rotate_invalid_token(self):
        """Should raise error for invalid token during rotation."""
        with pytest.raises(EncryptionError) as exc:
            rotate_encryption_key(
                ["invalid-encrypted-token"],
                "old-secret",
                "old-salt",
                "new-secret",
                "new-salt",
            )
        assert "Failed to rotate token at index 0" in str(exc.value)


class TestClearCache:
    """Tests for cache clearing."""

    def test_clear_encryption_cache(self):
        """Should clear the Fernet cache."""
        # Encrypt something to populate cache
        encrypt_token("test")

        # Clear cache
        clear_encryption_cache()

        # Should still work after cache clear
        encrypted = encrypt_token("test2")
        decrypted = decrypt_token(encrypted)
        assert decrypted == "test2"


class TestKeyDerivation:
    """Tests for key derivation."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_encryption_cache()

    @patch("src.config.settings")
    def test_uses_settings_secret_key(self, mock_settings):
        """Should use SECRET_KEY from settings."""
        mock_settings.SECRET_KEY = "test-secret-key-for-encryption!!"
        mock_settings.ENCRYPTION_SALT = "test-salt"

        clear_encryption_cache()
        encrypted = encrypt_token("test-token")
        decrypted = decrypt_token(encrypted)

        assert decrypted == "test-token"

    @patch("src.config.settings")
    def test_default_salt_when_missing(self, mock_settings):
        """Should use default salt if ENCRYPTION_SALT not set."""
        mock_settings.SECRET_KEY = "test-secret-key-for-encryption!!"
        # Don't set ENCRYPTION_SALT - getattr will return the default

        del mock_settings.ENCRYPTION_SALT

        clear_encryption_cache()

        encrypted = encrypt_token("test-token")
        decrypted = decrypt_token(encrypted)

        assert decrypted == "test-token"

    def test_different_keys_produce_different_ciphertext(self):
        """Different keys should produce incompatible ciphertext."""
        import base64
        import hashlib

        from cryptography.fernet import Fernet

        # Encrypt with key1
        key1_material = b"key1salt1"
        key1_derived = hashlib.sha256(key1_material).digest()
        fernet1 = Fernet(base64.urlsafe_b64encode(key1_derived))
        encrypted1 = fernet1.encrypt(b"secret").decode()

        # Try to decrypt with key2 - should fail
        key2_material = b"key2salt2"
        key2_derived = hashlib.sha256(key2_material).digest()
        fernet2 = Fernet(base64.urlsafe_b64encode(key2_derived))

        from cryptography.fernet import InvalidToken

        with pytest.raises(InvalidToken):
            fernet2.decrypt(encrypted1.encode())
