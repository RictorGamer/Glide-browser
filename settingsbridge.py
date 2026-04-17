import os
import sys
import json
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile

class SettingsBridge(QObject):
    def __init__(self, browser_app, parent=None):
        super().__init__(parent)
        self.app = browser_app
        # Жестко привязываем папку themes к директории запуска скрипта
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.themes_dir = os.path.join(base_dir, "themes")
        os.makedirs(self.themes_dir, exist_ok=True)
        defaul_theme = os.path.join(self.themes_dir, "default.qss")
        if not os.listdir(self.themes_dir):
            app_instance = QApplication.instance()
            if app_instance:
                with open(defaul_theme, "w",encoding="utf-8") as f:
                    f.write(app_instance.styleSheet())

    @pyqtSlot(result=str)
    def get_settings(self):
        data = {
            "homepage": self.app.config.get("homepage", ""),
            "search_engine": self.app.config.get("search_engine", "https://www.google.com/search?q="),
            "show_clock": self.app.config.get("show_clock", True),
            "show_search": self.app.config.get("show_search", True),
            "gpu_backend": self.app.config.get("gpu_backend", ""),
            "user_agent": self.app.config.get("user_agent", ""),
            "ui_theme": self.app.config.get("ui_theme", "dark"),
            "custom_qss": self.app.config.get("custom_qss", ""),  # FIX: Added custom_qss
            "notifications_enabled": self.app.config.get("notifications_enabled", True),
            "adblock": ", ".join(getattr(self.app.interceptor, 'blocked_domains', [])) if hasattr(self.app, 'interceptor') else "",
            "js_enabled": self.app.config.get("js_enabled", True),
            "img_enabled": self.app.config.get("img_enabled", True),
            "cookies_enabled": self.app.config.get("cookies_enabled", True)
        }
        return json.dumps(data)

    @pyqtSlot(str)
    def save_settings(self, settings_json):
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path = os.path.join(base_dir, "settings.json")
        data = json.loads(settings_json)
        
        self.app.config["homepage"] = data.get("homepage", "")
        self.app.config["search_engine"] = data.get("search_engine", "https://www.google.com/search?q=")
        self.app.config["show_clock"] = data.get("show_clock", True)
        self.app.config["show_search"] = data.get("show_search", True)
        self.app.config["user_agent"] = data.get("user_agent", "")
        self.app.config["gpu_backend"] = data.get("gpu_backend", "")
        self.app.config["ui_theme"] = data.get("ui_theme", "dark")
        self.app.config["notifications_enabled"] = data.get("notifications_enabled", True)
        self.app.config["adblock"] = data.get("adblock", "")
        self.app.config["js_enabled"] = data.get("js_enabled", True)
        self.app.config["img_enabled"] = data.get("img_enabled", True)
        self.app.config["cookies_enabled"] = data.get("cookies_enabled", True)

        profiles = list(self.app.profile_manager.active_profiles.values())
        if hasattr(self.app, 'profile'):
            profiles.append(self.app.profile)
            
        for prof in profiles:
            settings = prof.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, self.app.config["js_enabled"])
            settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, self.app.config["img_enabled"])
            
            if self.app.config["cookies_enabled"]:
                prof.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
            else:
                prof.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)


        if hasattr(self.app, 'clock_sb'):
            self.app.clock_sb.setVisible(self.app.config["show_clock"])
        if hasattr(self.app, 'search_sb'):
            self.app.search_sb.setVisible(self.app.config["show_search"])
        
        if hasattr(self.app, 'interceptor'):
            new_blocked = [d.strip() for d in data.get("adblock", "").split(",") if d.strip()]
            self.app.interceptor.update_domains(new_blocked)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.app.config, f, indent=4, ensure_ascii=False)



    @pyqtSlot()
    def clear_data(self):
        import shutil
        files_to_delete = ["bookmarks.json", "settings.json", "speeddial.json", "history.enc", "vault.enc", "downloads.json", "sync_config.json"]
        for f in files_to_delete:
            if os.path.exists(f): os.remove(f)
        if os.path.exists("storage"): shutil.rmtree("storage")
        if os.path.exists("glide_data"): shutil.rmtree("glide_data")

    @pyqtSlot(result=str)
    def get_themes(self):
        themes = [f for f in os.listdir(self.themes_dir) if f.endswith(".qss")]
        return json.dumps(themes)

    @pyqtSlot(str, result=str)
    def load_qss(self, filename):
        path = os.path.join(self.themes_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @pyqtSlot(str, str)
    def save_qss(self, filename, content):
        if not filename.endswith(".qss"):
            filename += ".qss"
        path = os.path.join(self.themes_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.app.config["theme_path"] = path
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.app.config, f, indent=4, ensure_ascii=False)
            
        self.apply_qss_now(content)

    @pyqtSlot(str)
    def apply_qss_now(self, content):
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.setStyleSheet(content)
