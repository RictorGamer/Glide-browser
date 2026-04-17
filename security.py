import os
import json
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

class VaultCrypto:
    def __init__(self, salt_file="vault.salt"):
        self.salt_file = salt_file
        self.key = None
        self._load_or_create_salt()

    def _load_or_create_salt(self):
        if not os.path.exists(self.salt_file):
            self.salt = os.urandom(16)
            with open(self.salt_file, "wb") as f:
                f.write(self.salt)
        else:
            with open(self.salt_file, "rb") as f:
                self.salt = f.read()

    def derive_key(self, password: str):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, # AES-256
            salt=self.salt,
            iterations=480000,
        )
        self.key = kdf.derive(password.encode())
        return self.key

    def verify_and_unlock(self, password: str, test_data: bytes):
        key = self.derive_key(password)
        try:
            aesgcm = AESGCM(key)
            nonce = test_data[:12]
            aesgcm.decrypt(nonce, test_data[12:], None)
            return True
        except (InvalidTag, Exception):
            self.key = None
            return False

    def generate_recovery_key(self):
        return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')

    def encrypt_data(self, data: str) -> bytes:
        if not self.key:
            raise ValueError("Ключ не инициализирован")
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        return nonce + ciphertext

    def decrypt_data(self, encrypted_data: bytes) -> str:
        if not self.key:
            raise ValueError("Ключ не инициализирован")
        aesgcm = AESGCM(self.key)
        nonce = encrypted_data[:12]
        plaintext = aesgcm.decrypt(nonce, encrypted_data[12:], None)
        return plaintext.decode('utf-8')

class HistoryCrypto:
    def __init__(self, key_file="browser.key"):
        self.key_file = key_file
        self._init_key()

    def _init_key(self):
        if not os.path.exists(self.key_file):
            self.key = AESGCM.generate_key(bit_length=256)
            with open(self.key_file, "wb") as f:
                f.write(self.key)
        else:
            with open(self.key_file, "rb") as f:
                self.key = f.read()
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, data: str) -> bytes:
        nonce = os.urandom(12)
        return nonce + self.aesgcm.encrypt(nonce, data.encode('utf-8'), None)

    def decrypt(self, encrypted_data: bytes) -> str:
        nonce = encrypted_data[:12]
        return self.aesgcm.decrypt(nonce, encrypted_data[12:], None).decode('utf-8')

class PermissionsManager:
    def __init__(self, file_path="permissions.json"):
        self.file_path = file_path
        self.permissions = self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def get_permission(self, host: str, feature: str):
        return self.permissions.get(host, {}).get(feature, None)

    def set_permission(self, host: str, feature: str, granted: bool):
        if host not in self.permissions:
            self.permissions[host] = {}
        self.permissions[host][feature] = granted
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.permissions, f)