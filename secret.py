import secrets
from typing import Optional


class MagmaCipher:
    """
    Упрощённая реализация шифра: по факту это XOR с ключом.
    Оставлен только для совместимости с остальным кодом, где вызывается generate_key().
    """

    _KEY_SIZE = 32  # 256-битный ключ

    def __init__(self, key: bytes):
        if len(key) != self._KEY_SIZE:
            raise ValueError(f"Key must be {self._KEY_SIZE} bytes")
        self._key = key

    @staticmethod
    def generate_key() -> bytes:
        """Генерирует случайный безопасный ключ."""
        return secrets.token_bytes(MagmaCipher._KEY_SIZE)

    @staticmethod
    def key_to_cpp(key: bytes) -> str:
        """Преобразует ключ в строку для вставки в C++ код (формат \xAB...)."""
        hex_parts = [f"\\x{b:02x}" for b in key]
        return "".join(hex_parts)

    def _xor(self, data: bytes) -> bytes:
        """Простейшее XOR-"шифрование" / расшифровка."""
        key = self._key
        key_len = len(key)
        return bytes(b ^ key[i % key_len] for i, b in enumerate(data))

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._xor(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        return self._xor(data)

    def encrypt(self, plaintext: str, encoding: str = "utf-8") -> bytes:
        return self.encrypt_bytes(plaintext.encode(encoding))

    def decrypt(self, ciphertext: bytes, encoding: str = "utf-8") -> str:
        return self.decrypt_bytes(ciphertext).decode(encoding, errors="ignore")


if __name__ == "__main__":
    # Небольшой тест
    key = MagmaCipher.generate_key()
    cipher = MagmaCipher(key)
    msg = "Привет, мир!"
    enc = cipher.encrypt(msg)
    dec = cipher.decrypt(enc)
    print("Исходное:", msg)
    print("Расшифровка:", dec)
