import hashlib
import hmac

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MEDIA_KEY_BYTES = 32
EXPANDED_KEY_BYTES = 112
IV_BYTES = 16
CIPHER_KEY_END = 48
MAC_KEY_END = 80
MAC_BYTES = 10
AES_BLOCK_BITS = 128
AES_BLOCK_BYTES = 16


class WhatsAppMediaCipher:
    def decrypt(
        self, encrypted: bytes, media_key: bytes, key_info: bytes
    ) -> bytes | None:
        ciphertext, mac = encrypted[:-MAC_BYTES], encrypted[-MAC_BYTES:]
        if (
            len(media_key) != MEDIA_KEY_BYTES
            or not ciphertext
            or len(ciphertext) % AES_BLOCK_BYTES
        ):
            return None
        expanded = HKDF(
            algorithm=hashes.SHA256(),
            length=EXPANDED_KEY_BYTES,
            salt=None,
            info=key_info,
        ).derive(media_key)
        iv = expanded[:IV_BYTES]
        cipher_key = expanded[IV_BYTES:CIPHER_KEY_END]
        mac_key = expanded[CIPHER_KEY_END:MAC_KEY_END]
        expected_mac = hmac.new(mac_key, iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_mac[:MAC_BYTES], mac):
            return None
        decryptor = Cipher(algorithms.AES(cipher_key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(AES_BLOCK_BITS).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
