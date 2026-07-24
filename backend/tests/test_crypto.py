import pytest
from app.core.crypto import encrypt_field, decrypt_field, mask_value


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        plain = "sk_live_1234567890abcdef"
        encrypted = encrypt_field(plain)
        assert encrypted != plain
        assert len(encrypted) > 0
        decrypted = decrypt_field(encrypted)
        assert decrypted == plain

    def test_encrypt_different_ciphertext_each_call(self):
        plain = "my_secret_value"
        c1 = encrypt_field(plain)
        c2 = encrypt_field(plain)
        assert c1 != c2

    def test_decrypt_invalid_base64_raises(self):
        with pytest.raises(ValueError):
            decrypt_field("!!invalid!!")

    def test_decrypt_tampered_raises(self):
        encrypted = encrypt_field("secret")
        tampered = encrypted[:-4] + "AAAA"
        with pytest.raises(ValueError):
            decrypt_field(tampered)

    def test_mask_value_default(self):
        assert mask_value("6222021234567890") == "************7890"

    def test_mask_value_custom_visible(self):
        assert mask_value("abcde", visible=2) == "***de"

    def test_mask_value_short(self):
        assert mask_value("ab", visible=4) == "**"

    def test_mask_value_empty(self):
        assert mask_value("") == ""
