import json
import os
import base64
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl, QByteArray, pyqtSignal, QObject
from security import VaultCrypto

class SyncManager(QObject):
    sync_completed = pyqtSignal(bool, str) # Успех, сообщение

    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager()
        self.crypto = VaultCrypto()
        self.sync_config = self.load_sync_config()

    def load_sync_config(self):
        path = "sync_config.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception: pass
        return {"global_server": "http://127.0.0.1:8000", "username": "default_user"}

    def save_sync_config(self, config):
        self.sync_config = config
        with open("sync_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def authenticate(self):
        server_url = self.sync_config.get("global_server", "http://127.0.0.1:8000")
        username = self.sync_config.get("username", "default_user")
        
        request = QNetworkRequest(QUrl(f"{server_url}/api/auth/register_or_login"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        data = json.dumps({"username": username}).encode('utf-8')
        
        reply = self.network_manager.post(request, QByteArray(data))
        reply.finished.connect(lambda: self._handle_auth(reply))

    def _handle_auth(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response = json.loads(reply.readAll().data().decode('utf-8'))
            self.sync_config["auth_token"] = response.get("token")
            self.save_sync_config(self.sync_config)
            self.sync_completed.emit(True, "Авторизация успешна. Токен получен.")
        else:
            self.sync_completed.emit(False, f"Ошибка авторизации: {reply.errorString()}")
        reply.deleteLater()

    def push_data(self, master_password: str):
        if not self.crypto.derive_key(master_password):
            self.sync_completed.emit(False, "Неверный мастер-пароль")
            return

        payload = {}
        if self.sync_config.get("sync_bookmarks", False):
            payload["bookmarks"] = self.encrypt_file("bookmarks.json")
        if self.sync_config.get("sync_settings", False): # Используем файл настроек
            payload["settings"] = self.encrypt_file("settings.json")
        if self.sync_config.get("sync_vault", False):
            payload["vault"] = self.encrypt_file("vault.enc", is_binary=True)

        server_url = self.sync_config.get("global_server", "http://127.0.0.1:8000")
        request = QNetworkRequest(QUrl(f"{server_url}/api/sync/push"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        token = self.sync_config.get("auth_token", "")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode('utf-8'))

        data = json.dumps({"payload": payload}).encode('utf-8')
        reply = self.network_manager.post(request, QByteArray(data))
        reply.finished.connect(lambda: self._handle_push(reply))

    def _handle_push(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.sync_completed.emit(True, "Данные успешно отправлены на сервер")
        else:
            self.sync_completed.emit(False, reply.errorString())
        reply.deleteLater()

    def pull_data(self, master_password: str):
        self.crypto.derive_key(master_password)
        server_url = self.sync_config.get("global_server", "http://127.0.0.1:8000")
        request = QNetworkRequest(QUrl(f"{server_url}/api/sync/pull"))
        token = self.sync_config.get("auth_token", "")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode('utf-8'))

        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self._handle_pull(reply))

    def _handle_pull(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response = json.loads(reply.readAll().data().decode('utf-8'))
            payload = response.get("payload", {})
            
            if payload.get("bookmarks") and self.sync_config.get("sync_bookmarks", False):
                self.decrypt_and_save(payload["bookmarks"], "bookmarks.json")
            if payload.get("settings") and self.sync_config.get("sync_settings", False):
                self.decrypt_and_save(payload["settings"], "settings.json")
            if payload.get("vault") and self.sync_config.get("sync_vault", False):
                self.decrypt_and_save(payload["vault"], "vault.enc", is_binary=True)
                
            self.sync_completed.emit(True, "Данные успешно загружены и расшифрованы")
        else:
            self.sync_completed.emit(False, reply.errorString())
        reply.deleteLater()

    def encrypt_file(self, filepath: str, is_binary=False) -> str:
        if not os.path.exists(filepath): return ""
        mode = "rb" if is_binary else "r"
        with open(filepath, mode) as f:
            data = f.read()
        
        if not is_binary: data = data.encode('utf-8')
        encrypted_bytes = self.crypto.encrypt_data(data.decode('utf-8') if not is_binary else str(data))
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt_and_save(self, encrypted_b64: str, filepath: str, is_binary=False):
        try:
            encrypted_bytes = base64.b64decode(encrypted_b64)
            decrypted_data = self.crypto.decrypt_data(encrypted_bytes)
            mode = "wb" if is_binary else "w"
            with open(filepath, mode) as f:
                if is_binary: f.write(decrypted_data.encode() if isinstance(decrypted_data, str) else decrypted_data)
                else: f.write(decrypted_data)
        except Exception as e:
            print(f"Ошибка расшифровки для {filepath}: {e}")
