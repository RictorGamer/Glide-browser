import sys
import json
import os
import shutil
import base64
import psutil
import shutil
from datetime import datetime
from urllib.parse import quote, unquote
# os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
#     "--ignore-gpu-blocklist "
#     "--enable-gpu-rasterization "
#     "--enable-accelerated-video-decode "
#     "--use-angle=d3d11 "                # Используем OpenGL через прослойку ANGLE
#     "--disable-direct-composition "  # Полное отключение DirectComposition
#     "--disable-direct-composition-layers "
#     "--disable-features=DirectCompositionVideoOverlays,HardwareProtectedVideoDecode "
#     "--disable-gpu-memory-buffer-video-frames " # Заставляем видео идти через обычную память
#     "--disable-features=UseSkiaRenderer" # Возвращаем старый рендерер, если новый багует
# )


from PyQt6.QtCore import QUrl, Qt, QSize,QUrlQuery,QTimer,QPropertyAnimation,QEasingCurve,pyqtSignal,QFile,QIODevice
from PyQt6.QtGui import QAction, QKeySequence,QIcon
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar, QMenu,
                             QLineEdit, QTabWidget, QWidget, QVBoxLayout, 
                             QToolButton, QMessageBox, QDialog, QFormLayout,
                             QComboBox, QPushButton, QHBoxLayout,
                             QListWidget, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QProgressBar, QSizePolicy,QLabel,
                             QSizePolicy,QSpacerItem,QFileDialog,QInputDialog,
                             QDockWidget,QListWidgetItem,QCheckBox,QFrame,QGraphicsOpacityEffect,QStackedWidget)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (QWebEngineProfile, QWebEnginePage,QWebEngineDownloadRequest,QWebEngineUrlRequestInterceptor,QWebEngineSettings,QWebEngineScript,QWebEngineUrlRequestInfo)
from security import VaultCrypto, HistoryCrypto, PermissionsManager
from study_mode import StudyManager
from profiles import ProfileManager
from macro_manager import MacroManager
from sync_manager import SyncManager
import weakref
from settings_ui_components import apply_modern_style
from settingsbridge import SettingsBridge

# --- Конфигурация ---
DOWNLOADS_FILE = "downloads.json"
SETTINGS_FILE = "settings.json"
HISTORY_FILE = "history.json"
VAULT_FILE = "vault.json"
DEFAULT_SETTINGS = {"homepage": "", "search_engine": "https://www.google.com/search?q=", "show_clock": True, "show_search": True}
import platform
print(platform.system())
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return default

config = load_json("settings.json", {})
gpu_backend = config.get("gpu_backend", "default")

base_flags = (
    "--ignore-gpu-blocklist "
    "--enable-gpu-rasterization "
    "--enable-accelerated-video-decode "
    "--use-angle=d3d11 "                # Используем OpenGL через прослойку ANGLE
    "--disable-direct-composition "  # Полное отключение DirectComposition
    "--disable-features=DirectCompositionVideoOverlays,HardwareProtectedVideoDecode "
    "--enable-gpu-memory-buffer-video-frames " # Заставляем видео идти через обычную память
    "--disable-features=UseSkiaRenderer" # Возвращаем старый рендерер, если новый багует
    "--enable-features=PictureInPicture"
)

if gpu_backend == "d3d11":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = base_flags + "--use-angle=d3d11 "
elif gpu_backend == "gl":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = base_flags + "--use-angle=gl "
else:
    # По умолчанию
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = base_flags

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

import subprocess

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QPlainTextEdit, QFileDialog, QMessageBox, QLabel)
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
from PyQt6.QtCore import QRegularExpression, Qt

class GlideWebView(QWebEngineView):
    def contextMenuEvent(self, event):
        # Создаем стандартное меню
        menu = self.page().createStandardContextMenu()
        
        # Добавляем разделитель и пункт
        menu.addSeparator()
        pip_action = menu.addAction("Режим PiP (Картинка в картинке)")
        # Используем лямбду, чтобы передать контекст
        pip_action.triggered.connect(self.force_pip)
        
        menu.exec(event.globalPos())

    def force_pip(self):
        # Этот скрипт ищет ПЕРВОЕ попавшееся видео на странице и пускает его в PiP
        js_code = """
        (async function() {
            try {
                const video = document.querySelector('video');
                if (video) {
                    if (document.pictureInPictureElement) {
                        await document.exitPictureInPicture();
                    } else {
                        await video.requestPictureInPicture();
                    }
                } else {
                    alert("Видео на этой странице не найдено");
                }
            } catch (e) {
                console.error(e);
            }
        })();
        """
        self.page().runJavaScript(js_code)


class AccountSettingsPage(QWidget):
    loadProgress = pyqtSignal(int)
    titleChanged = pyqtSignal(int)
    urlChanged = pyqtSignal(QUrl)


    def __init__(self,browser_app=None, parent=None):
        super().__init__(parent)
        self.browser_app = browser_app
        self.setObjectName("AccountPage")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Левая колонка навигации
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(221)
        self.sidebar.setObjectName("AccountSidebar")
        self.sidebar.setContentsMargins(-10, -10, -10, -10)
        self.sidebar.setSpacing(15)
        
        # Правая часть с контентом
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("AccountContentStack")

        self.layout.addWidget(self.sidebar)
        self.layout.addWidget(self.content_stack)

        self.setup_ui()

    def setPage(self,page):
        pass

    def page(self):
        return None

    def url(self):
        return QUrl("glide://profile-settings")

    def setup_ui(self):
        # Группировка разделов
        sections = [
            ("👤 Профиль", ProfileView()),
            ("📂 Контент и данные", DataView(self.browser_app)),
            ("🔄 Синхронизация", SyncView()),
            ("🛡 Безопасность", SecurityView()),
            ("💻 Устройства", DeviceView()),
            ("👨‍👩‍👧‍👦 Семейный центр", FamilyView()),
            ("⚙ Управление аккаунтом", DangerZoneView())
        ]

        for name, widget in sections:
            item = QListWidgetItem(name)
            self.sidebar.addItem(item)
            self.content_stack.addWidget(widget)

        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

class SyncView(QWidget):
    def __init__(self):
        super().__init__()
        self.sync_manager = SyncManager()
        self.sync_manager.sync_completed.connect(self.on_sync_result)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.server_url = QLineEdit()
        self.server_url.setText(self.sync_manager.sync_config.get("global_server", "http://127.0.0.1:8000"))
        
        self.username = QLineEdit()
        self.username.setPlaceholderText("Имя пользователя")
        self.username.setText(self.sync_manager.sync_config.get("username", ""))
        
        self.sync_bookmarks = QCheckBox("Синхронизировать закладки")
        self.sync_bookmarks.setChecked(self.sync_manager.sync_config.get("sync_bookmarks", False))
        
        self.sync_settings = QCheckBox("Синхронизировать настройки")
        self.sync_settings.setChecked(self.sync_manager.sync_config.get("sync_settings", False))
        
        self.sync_vault = QCheckBox("Синхронизировать зашифрованное хранилище")
        self.sync_vault.setChecked(self.sync_manager.sync_config.get("sync_vault", False))
        
        self.master_password = QLineEdit()
        self.master_password.setPlaceholderText("Мастер-пароль (для E2E шифрования)")
        self.master_password.setEchoMode(QLineEdit.EchoMode.Password)

        btn_auth = QPushButton("Авторизоваться / Получить токен")
        btn_auth.clicked.connect(self.save_and_auth)
        
        btn_push = QPushButton("Выгрузить в облако (Push)")
        btn_push.clicked.connect(lambda: self.sync_manager.push_data(self.master_password.text()))
        
        btn_pull = QPushButton("Загрузить из облака (Pull)")
        btn_pull.clicked.connect(lambda: self.sync_manager.pull_data(self.master_password.text()))

        for w in [self.server_url, self.username, self.sync_bookmarks, self.sync_settings, self.sync_vault, self.master_password, btn_auth, btn_push, btn_pull]:
            if hasattr(w, 'setStyleSheet'): apply_modern_style(w)
            layout.addWidget(w)

        layout.addStretch()
        self.setLayout(layout)

    def save_and_auth(self):
        config = self.sync_manager.sync_config
        config["global_server"] = self.server_url.text()
        config["username"] = self.username.text()
        config["sync_bookmarks"] = self.sync_bookmarks.isChecked()
        config["sync_settings"] = self.sync_settings.isChecked()
        config["sync_vault"] = self.sync_vault.isChecked()
        self.sync_manager.save_sync_config(config)
        self.sync_manager.authenticate()

    def on_sync_result(self, success, msg):
        if success:
            QMessageBox.information(self, "Синхронизация", msg)
        else:
            QMessageBox.warning(self, "Ошибка", msg)

class SecurityView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QLabel("БЕЗОПАСНОСТЬ ДАННЫХ"))
        
        self.change_pass_btn = QPushButton("Изменить мастер-пароль")
        self.enable_2fa = QCheckBox("Включить локальную двухфакторную аутентификацию")
        self.auto_lock = QComboBox()
        self.auto_lock.addItems(["Никогда", "Через 5 минут", "Через 30 минут"])
        
        apply_modern_style(self.change_pass_btn)
        apply_modern_style(self.enable_2fa)
        
        layout.addWidget(self.change_pass_btn)
        layout.addWidget(self.enable_2fa)
        layout.addWidget(QLabel("Автоблокировка хранилища:"))
        layout.addWidget(self.auto_lock)
        layout.addStretch()
        self.setLayout(layout)
        
class DeviceView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("background-color: #121212; border: 1px solid #333; color: white;")
        

        import platform
        system = platform.system
        item = QListWidgetItem(f"Текущее устройство: {system}")
        self.device_list.addItem(item)
        
        layout.addWidget(QLabel("ПОДКЛЮЧЕННЫЕ УСТРОЙСТВА"))
        layout.addWidget(self.device_list)
        
        btn_revoke = QPushButton("Отключить все устройства")
        apply_modern_style(btn_revoke)
        layout.addWidget(btn_revoke)
        layout.addStretch()
        self.setLayout(layout)
        
class FamilyView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QLabel("ПРОФИЛИ И ДОСТУП"))
        
        self.profile_selector = QComboBox()
        self.profile_selector.addItems(["Основной профиль", "Гостевой режим", "Учебный профиль"])
        
        self.restrict_mode = QCheckBox("Ограничить доступ к настройкам шифрования")
        apply_modern_style(self.restrict_mode)
        
        layout.addWidget(QLabel("Активный профиль:"))
        layout.addWidget(self.profile_selector)
        layout.addWidget(self.restrict_mode)
        layout.addStretch()
        self.setLayout(layout)
        
        

class DataView(QWidget):
    def __init__(self, browser_app=None):
        super().__init__()
        self.browser_app = browser_app
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        btn_export = QPushButton("Экспорт всех данных (JSON)")
        btn_export.clicked.connect(self.export_data)
        
        btn_clear = QPushButton("ПОЛНАЯ ОЧИСТКА БРАУЗЕРА")
        btn_clear.setStyleSheet("background-color: #441111; color: white; border: 1px solid #662222; padding: 10px;")
        btn_clear.clicked.connect(self.clear_all_data)
        
        apply_modern_style(btn_export)
        
        layout.addWidget(btn_export)
        layout.addSpacing(20)
        layout.addWidget(btn_clear)
        layout.addStretch()
        self.setLayout(layout)

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить экспорт", "glide_export.json", "JSON (*.json)")
        if not path: return
        
        export_dict = {}
        for file in ["bookmarks.json", "settings.json", "speeddial.json"]:
            if os.path.exists(file):
                with open(file, 'r', encoding='utf-8') as f:
                    export_dict[file] = json.load(f)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(export_dict, f, indent=4)
        QMessageBox.information(self, "Успех", "Данные экспортированы.")

    def clear_all_data(self):
        confirm = QMessageBox.question(self, "Внимание", "Это удалит кэш, историю, закладки и профили. Продолжить?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            files_to_delete = ["bookmarks.json", "settings.json", "speeddial.json", "history.enc", "vault.enc", "downloads.json", "sync_config.json"]
            for f in files_to_delete:
                if os.path.exists(f): os.remove(f)
            
            if os.path.exists("storage"): shutil.rmtree("storage")
            if os.path.exists("glide_data"): shutil.rmtree("glide_data")
            
            QMessageBox.information(self, "Очистка", "Данные удалены. Перезапустите приложение.")

class ProfileView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Заголовок
        title = QLabel("Мой профиль")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #fff;")
        layout.addWidget(title)

        # Секция аватара и инфо
        info_layout = QHBoxLayout()
        avatar_label = QLabel()
        avatar_label.setFixedSize(80, 80)
        avatar_label.setStyleSheet("background-color: #333; border-radius: 40px; border: 2px solid #0078d4;")
        
        details = QVBoxLayout()
        name_label = QLabel("None")
        name_label.setStyleSheet("font-size: 18px; color: #eee;")
        status_label = QLabel("Статус: Разработчик")
        status_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        
        details.addWidget(name_label)
        details.addWidget(status_label)
        info_layout.addWidget(avatar_label)
        info_layout.addLayout(details)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        layout.addSpacing(30)
        
        # Поля почты и прочего
        form = QFormLayout()
        form.setSpacing(15)
        form.addRow("Привязанная почта:", QLineEdit("example@example.com"))
        layout.addLayout(form)
        layout.addStretch()

class DangerZoneView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("Управление аккаунтом")
        title.setStyleSheet("font-size: 24px; color: #ff4444;")
        layout.addWidget(title)
        
        logout_btn = QPushButton("Выйти из системы")
        delete_btn = QPushButton("Удалить аккаунт")
        delete_btn.setObjectName("dangerBtn") # Используем ваш стиль из QSS
        
        layout.addWidget(logout_btn)
        layout.addWidget(delete_btn)
        layout.addStretch()

     

class StudyUIWidget(QFrame):
    def __init__(self, study_manager):
        super().__init__()
        self.manager = study_manager
        self.setObjectName("StudyWidget")
        self.setFixedWidth(200)
        
        # Стилизация в темных тонах
        self.setStyleSheet("""
            #StudyWidget {
                background-color: #1e1e1e;
                border-left: 1px solid #333;
                padding: 10px;
            }
            QLabel { color: #ffffff; font-weight: bold; }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2b88d8; }
            QPushButton#stopBtn { background-color: #d83b01; }
            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px;
                text-align: center;
                height: 10px;
            }
            QProgressBar::chunk { background-color: #0078d4; }
        """)

        layout = QVBoxLayout()
        self.title = QLabel("Фокус на учебе")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.timer_label = QLabel("25:00")
        self.timer_label.setStyleSheet("font-size: 24px; margin: 10px 0;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 25 * 60)
     
class ProfileSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор контейнера")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        self.label = QLabel("Введите имя профиля (контейнера):")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Например: Work, Social, Study...")
        self.input.setText("Default")
        
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Открыть")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_profile_name(self):
        return self.input.text().strip() or "Default"

class DownloadItemWidget(QWidget):
    def __init__(self, download_item, parent_list_widget):
        super().__init__()
        self.download_item = download_item
        self.parent_list = parent_list_widget
        self.file_path = ""
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # Информационная строка
        info_layout = QHBoxLayout()
        self.name_label = QLabel(download_item.downloadFileName())
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.status_label = QLabel("0%")
        self.status_label.setStyleSheet("color: #888;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_label)
        layout.addLayout(info_layout)

        # Полоска прогресса
        self.bar = QProgressBar()
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        self.open_folder_btn = QPushButton("📁")
        self.open_folder_btn.setFixedSize(28, 24) # Узкие кнопки
        self.open_folder_btn.setToolTip("Открыть папку")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_folder)

        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(28, 24)
        self.cancel_btn.setToolTip("Отмена/Удалить")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.clicked.connect(self.cancel_download)

        btn_layout.addStretch()
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Сигналы обновления
        download_item.receivedBytesChanged.connect(self.update_progress)
        download_item.stateChanged.connect(self.on_state_changed)

    def update_progress(self):
        total = self.download_item.totalBytes()
        received = self.download_item.receivedBytes()
        if total > 0:
            prog = int(received * 100 / total)
            self.bar.setValue(prog)
            self.status_label.setText(f"{prog}%")

    def on_state_changed(self,state):
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.fade_anim = QPropertyAnimation(self.bar, b"maximumHeight")
            self.fade_anim.setDuration(400)
            self.fade_anim.setStartValue(self.bar.height())
            self.fade_anim.setEndValue(0)
            self.fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
            self.fade_anim.start()
            self.bar.hide()
            self.status_label.setText("Готово")
            self.open_folder_btn.setEnabled(True)
            self.file_path = self.download_item.downloadDirectory() + "/" + self.download_item.downloadFileName()

    def open_folder(self):
        import platform
        folder = os.path.dirname(self.file_path)
        system = platform.system()
        if system == "Windows":
            os.startfile(folder)
        elif system == "Darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(['xdg-open', folder])

    def cancel_download(self):
        if self.download_item.state() == QWebEngineDownloadRequest.DownloadState.DownloadInProgress:
            self.download_item.cancel()
        # Удаляем сам виджет из списка
        for i in range(self.parent_list.count()):
            item = self.parent_list.item(i)
            if self.parent_list.itemWidget(item) == self:
                self.parent_list.takeItem(i)
                break

class SidebarWidget(QWidget):
    def __init__(self, parent_browser):
        super().__init__()
        self.browser = parent_browser
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Боковые вкладки (позиция слева - West, для компактности)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("sidebarTabs")
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.layout.addWidget(self.tabs)

        self.setup_history_tab()
        self.setup_notes_tab()
        self.setup_messengers_tab()
        self.setup_monitor_tab()
        self.setup_downloads_tab()
        self.setup_study_tab()
        self.setup_macros_tab()

    def setup_study_tab(self):
        study_widget = QWidget()
        layout = QVBoxLayout(study_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Фокус на учебе")
        title.setStyleSheet("font-size: 14px; color: #89b4fa; margin-bottom: 10px;")
        layout.addWidget(title)

        self.study_timer_label = QLabel("25:00")
        self.study_timer_label.setStyleSheet("font-size: 32px; font-weight: 200; margin: 20px 0;")
        self.study_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.study_timer_label)

        self.study_btn = QPushButton("Начать сессию")
        self.study_btn.setObjectName("primaryBtn")
        self.study_btn.clicked.connect(self.browser.toggle_study_mode)
        layout.addWidget(self.study_btn)

        info = QLabel("Блокировка отвлекающих ресурсов активна во время сессии.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 11px; margin-top: 10px;")
        layout.addWidget(info)
        
        self.tabs.addTab(study_widget, "🎓")

    def setup_macros_tab(self):
        macro_widget = QWidget()
        layout = QVBoxLayout(macro_widget)

        layout.addWidget(QLabel("JS Макросы"))
        
        self.macro_list = QListWidget()
        # Предполагается, что macro_manager добавлен в BrowserApp
        if hasattr(self.browser, 'macro_manager'):
            self.macro_list.addItems(self.browser.macro_manager.macros.keys())
        
        layout.addWidget(self.macro_list)

        run_btn = QPushButton("Запустить")
        run_btn.clicked.connect(self.browser.run_selected_macro)
        layout.addWidget(run_btn)
        
        self.tabs.addTab(macro_widget, "📜")

    def setup_history_tab(self):
        # Адаптация существующей истории
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        refresh_btn = QPushButton("Очистить")
        refresh_btn.clicked.connect(self.load_history)
        layout.addWidget(refresh_btn)
        
        self.tabs.addTab(history_widget, "🕒")
        self.load_history()

    def load_history(self):
        self.history_list.clear()
        if hasattr(self.browser, 'history_cache'):
            for item in reversed(self.browser.history_cache[-50:]): # Последние 50
                list_item = QListWidgetItem(f"{item['time']}\n{item['title']}")
                list_item.setData(Qt.ItemDataRole.UserRole,item['url'])
                self.history_list.addItem(list_item)
            try:
                self.history_list.itemDoubleClicked.disconnect()
            except TypeError:
                pass
            self.history_list.itemDoubleClicked.connect(lambda item: self.browser.add_new_tab(QUrl(item.data(Qt.ItemDataRole.UserRole)),"Из истории"))

    def setup_notes_tab(self):
        from PyQt6.QtWidgets import QTextEdit
        notes_widget = QWidget()
        layout = QVBoxLayout(notes_widget)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Поддерживается синтаксис Markdown...")
        
        # Загрузка заметок
        self.notes_file = "notes.md"
        if os.path.exists(self.notes_file):
            with open(self.notes_file, "r", encoding="utf-8") as f:
                self.notes_edit.setMarkdown(f.read())
                
        self.notes_edit.textChanged.connect(self.save_notes)
        layout.addWidget(self.notes_edit)
        self.tabs.addTab(notes_widget, "📝")

    def save_notes(self):
        with open(self.notes_file, "w", encoding="utf-8") as f:
            f.write(self.notes_edit.toPlainText())

    def setup_messengers_tab(self):
        self.msg_widget = QWidget()
        layout = QVBoxLayout(self.msg_widget)
        
        combo = QComboBox()
        combo.addItems(["Telegram", "WhatsApp", "Discord"])
        layout.addWidget(combo)

        self.msg_view = QWebEngineView()
        self.msg_profile = QWebEngineProfile("Messengers", self.msg_view)
        # Мобильный User-Agent для компактного вида
        self.msg_profile.setHttpUserAgent("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36")
        
        msg_page = QWebEnginePage(self.msg_profile, self.msg_view)
        self.msg_view.setPage(msg_page)
        layout.addWidget(self.msg_view)

        self.urls = {"Telegram": "https://web.telegram.org/k/", "WhatsApp": "https://web.whatsapp.com/", "Discord": "https://discord.com/channels/@me"}
        combo.currentTextChanged.connect(lambda t: self.msg_view.setUrl(QUrl(self.urls[t])))
        self.msg_view.setUrl(QUrl(self.urls["Telegram"]))

        self.tabs.addTab(self.msg_widget, "💬")

        # Таймер выгрузки (10 минут)
        self.unload_timer = QTimer(self)
        self.unload_timer.setInterval(600000) 
        self.unload_timer.timeout.connect(self.unload_messenger)
        
        self.tabs.currentChanged.connect(self.check_messenger_visibility)

    def check_messenger_visibility(self):
        if self.tabs.currentWidget() == self.msg_widget:
            self.unload_timer.stop()
            if self.msg_view.url().isEmpty():
                self.msg_view.reload() # Восстановление сессии
        else:
            self.unload_timer.start()

    def unload_messenger(self):
        self.msg_view.setUrl(QUrl("about:blank")) # Очистка памяти

    def setup_monitor_tab(self):
        monitor_widget = QWidget()
        layout = QVBoxLayout(monitor_widget)
        self.ram_label = QLabel("ОЗУ: Вычисление...")
        self.ram_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ram_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #a6e3a1;")
        layout.addWidget(self.ram_label)

        self.ram_timer = QTimer(self)
        self.ram_timer.timeout.connect(self.update_ram)
        self.ram_timer.start(2000) # Обновление каждые 2 секунды
        self.tabs.addTab(monitor_widget, "📊")

    def update_ram(self):
        try:
            current_process = psutil.Process(os.getpid())
            total_mem = current_process.memory_info().rss
            # Суммируем память дочерних процессов QtWebEngine
            for child in current_process.children(recursive=True):
                total_mem += child.memory_info().rss
            
            mb = total_mem / (1024 * 1024)
            self.ram_label.setText(f"Общее потребление:\n{mb:.1f} MB")
        except Exception:
            self.ram_label.setText("Ошибка доступа к ОЗУ")
    def setup_downloads_tab(self):
        dl_widget = QWidget()
        layout = QVBoxLayout(dl_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.downloads_list = QListWidget()
        self.downloads_list.setStyleSheet("QListWidget::item { border-bottom: 1px solid #222; }")
        layout.addWidget(self.downloads_list)
        
        self.tabs.addTab(dl_widget, "📥")

    def add_download_to_list(self, download_item):
        item = QListWidgetItem(self.downloads_list)
        # Создаем кастомный виджет
        widget = DownloadItemWidget(download_item, self.downloads_list)
        item.setSizeHint(widget.sizeHint())
        self.downloads_list.addItem(item)
        self.downloads_list.setItemWidget(item, widget)
        # Переключаемся на вкладку загрузок автоматически
        self.tabs.setCurrentWidget(self.downloads_list.parentWidget())

class CustomWebPage(QWebEnginePage):
    def __init__(self, profile, parent_window, destination_webview):
        super().__init__(profile, destination_webview)
        self.parent_window = parent_window
        self.inject_sandbox_script()



    def inject_sandbox_script(self):
        # Скрипт отслеживает не доверенные клики (вызванные скриптами, а не физически)
        script = QWebEngineScript()
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setName("SandboxJS")
        js_code = """
        document.addEventListener('click', function(e) {
            if (!e.isTrusted && e.target.tagName !== 'A') {
                e.preventDefault();
                e.stopPropagation();
                window.location.href = "browser:macro-blocked?target=" + encodeURIComponent(e.target.tagName);
            }
        }, true);
        """
        script.setSourceCode(js_code)
        self.profile().scripts().insert(script)

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if url.scheme() == "browser":
            path = url.path()
            query = QUrlQuery(url.query())
            
            if path == "https-warning":
                target_url = unquote(query.queryItemValue("url"))
                host = unquote(query.queryItemValue("host"))
                self.parent_window.show_https_warning(self.view(), target_url, host)
                return False
                
            elif path == "macro-blocked":
                target = unquote(query.queryItemValue("target"))
                QMessageBox.warning(self.parent_window, "Защита", f"Заблокирована попытка скрипта нажать на элемент: {target}")
                return False
            

            elif path == "trust-http":
                host = query.queryItemValue("host")
                target_url = unquote(query.queryItemValue("url"))
                self.parent_window.interceptor.trust_host(host)
                self.view().setUrl(QUrl(target_url))
                return False

            index = query.queryItemValue("index") # Получаем индекс плитки
            if path == "add-speed-dial":
                self.parent_window.add_speed_dial_item()
            elif path == "edit-speed-dial" and index:
                self.parent_window.edit_speed_dial_item(int(index))
            elif path == "delete-speed-dial" and index:
                self.parent_window.delete_speed_dial_item(int(index))
            elif path == "search":
                search_query = query.queryItemValue("query")
                if search_query:
                    # Декодируем запрос и передаем в адресную строку
                    decoded_query = unquote(search_query)
                    self.parent_window.url_bar.setText(decoded_query)
                    QTimer.singleShot(0,self.parent_window.navigate_to_url)
                    #self.parent_window.navigate_to_url()
            
            return False # Блокируем реальный переход
        return super().acceptNavigationRequest(url, _type, isMainFrame)
    
    def createWindow(self, _type):
        new_browser = self.parent_window.add_new_tab(QUrl("about:blank"), "Новая вкладка")
        return new_browser.page()


class SecurityInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.block_file = "blocked_domains.json"
        self.trusted_http_file = "trusted_http.json"
        self.blocked_domains = load_json(self.block_file, ["doubleclick.net", "googleadservices.com"])
        self.trusted_http = load_json(self.trusted_http_file, [])

        self.study_mode_active = False
        self.study_blocklist = []

    def interceptRequest(self, info):
        url_obj = info.requestUrl()
        url_str = url_obj.toString()
        host = url_obj.host()

        if self.study_mode_active:
            for domain in self.study_blocklist:
                if domain in host:
                    info.block(True)
                    return

        # 1. AdBlock
        for domain in self.blocked_domains:
            if domain in url_str:
                info.block(True)
                return

        # 2. HTTPS Only Mode
        if url_obj.scheme() == "http" and host not in self.trusted_http and host not in ["localhost", "127.0.0.1"] and info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            # Блокируем HTTP запрос и перенаправляем на защищенную страницу-заглушку
            info.block(True)
            info.redirect(QUrl(f"browser:https-warning?url={quote(url_str)}&host={quote(host)}"))

    def trust_host(self, host):
        if host not in self.trusted_http:
            self.trusted_http.append(host)
            save_json(self.trusted_http_file, self.trusted_http)
    
    def update_domains(self, domains):
        self.blocked_domains = domains
        save_json(self.block_file,self.blocked_domains)

# --- Диалоговые окна ---
class HistoryDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🕒 Журнал посещений")
        self.setFixedSize(700, 450)
        layout = QVBoxLayout(self)

        self.browser = parent

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 10px; border-bottom: 1px solid #2a2a2a; }")
        self.list_widget.itemDoubleClicked.connect(self.open_history_item)
        layout.addWidget(self.list_widget)

        self.clear_btn = QPushButton("🗑 Полная очистка истории")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.clicked.connect(self.clear_history)
        layout.addWidget(self.clear_btn)
        self.load_history()

    def load_history(self):
        self.list_widget.clear()
        if hasattr(self.browser, 'history_cache'):
            for item in reversed(self.browser.history_cache):
                list_item = QListWidgetItem(f"{item['time']} | {item['title']}\n{item['url']}")
                list_item.setData(Qt.ItemDataRole.UserRole,item['url'])
                self.list_widget.addItem(list_item)
    
    def open_history_item(self,item):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.browser.add_new_tab(QUrl(url), "Из истории")
            self.accept()

    def clear_history(self):
        if hasattr(self.browser, 'history_cache'):
            self.browser.history_cache.clear()
            self.browser.save_encrypted_history()
            self.list_widget.clear()
            QMessageBox.information(self,"История","История посещений очищена")

class PasswordVaultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.crypto = VaultCrypto()
        self.setWindowTitle("🔑 Сейф паролей - Авторизация")
        self.setFixedSize(400, 200)
        self.setup_auth_ui()

    def setup_auth_ui(self):
        self.layout = QVBoxLayout(self)
        self.info_label = QLabel("Введите Мастер-пароль для доступа к сейфу.")
        self.layout.addWidget(self.info_label)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.pass_input)

        self.auth_btn = QPushButton("Разблокировать")
        self.auth_btn.setObjectName("primaryBtn")
        self.auth_btn.clicked.connect(self.authenticate)
        self.layout.addWidget(self.auth_btn)

    def authenticate(self):
        pwd = self.pass_input.text()
        vault_path = "vault.enc"
        
        if not os.path.exists(vault_path):
            # Первичная настройка
            self.crypto.derive_key(pwd)
            recovery = self.crypto.generate_recovery_key()
            QMessageBox.information(self, "Инициализация", f"Сейф создан.\nВаш ключ восстановления (сохраните его!): {recovery}")
            # Сохраняем пустой зашифрованный сейф (тестовые данные для проверки пароля в будущем)
            encrypted = self.crypto.encrypt_data(json.dumps([]))
            with open(vault_path, "wb") as f: f.write(encrypted)
            self.load_main_ui([])
            return

        # Проверка пароля
        with open(vault_path, "rb") as f:
            encrypted = f.read()
        
        if self.crypto.verify_and_unlock(pwd, encrypted):
            try:
                decrypted = self.crypto.decrypt_data(encrypted)
                data = json.loads(decrypted)
                self.load_main_ui(data)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", "Не удалось расшифровать данные.")
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный пароль.")

    def load_main_ui(self, data):
        # Удаляем элементы авторизации
        for i in reversed(range(self.layout.count())): 
            self.layout.itemAt(i).widget().deleteLater()
            
        self.setFixedSize(700, 450)
        self.setWindowTitle("🔑 Сейф паролей")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Ресурс", "Логин", "Пароль"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.clicked.connect(self.add_row)
        
        self.save_btn = QPushButton("💾 Сохранить изменения")
        self.save_btn.clicked.connect(self.save_vault)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.save_btn)
        self.layout.addLayout(btn_layout)
        
        self.populate_table(data)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(item.get('site', '')))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('login', '')))
            self.table.setItem(row, 2, QTableWidgetItem(item.get('password', '')))

    def add_row(self):
        self.table.insertRow(self.table.rowCount())

    def save_vault(self):
        vault = []
        for row in range(self.table.rowCount()):
            site = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            login = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            raw_pass = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
            
            if site or login:
                vault.append({"site": site, "login": login, "password": raw_pass})
                
        # Шифрование и сохранение
        encrypted = self.crypto.encrypt_data(json.dumps(vault))
        with open("vault.enc", "wb") as f:
            f.write(encrypted)
        QMessageBox.information(self, "Успех", "Зашифрованные данные сохранены!")

class BookmarksDialog(QDialog):
    def __init__(self, parent_browser):
        super().__init__(parent_browser)
        self.browser = parent_browser
        self.setWindowTitle("⭐ Управление закладками")
        self.setFixedSize(500, 300)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.del_btn = QPushButton("🗑 Удалить выбранную")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self.delete_bookmark)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)

        self.load_bookmarks_list()

    def load_bookmarks_list(self):
        self.list_widget.clear()
        bms = load_json("bookmarks.json", {})
        for title, url in bms.items():
            self.list_widget.addItem(f"{title} | {url}")

    def delete_bookmark(self):
        selected = self.list_widget.currentItem()
        if not selected: return
        title = selected.text().split(" | ")[0]
        
        bms = load_json("bookmarks.json", {})
        if title in bms:
            del bms[title]
            save_json("bookmarks.json", bms)
            self.load_bookmarks_list()
            self.browser.load_bookmarks() # Обновляем панель в браузере

# --- Главное окно ---
class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.setWindowTitle("Glide browser [DEV BUILD] v1.2.2")
        self.resize(1280, 800)

        pip_shortcut = QAction("Toggle Pip", self)
        pip_shortcut.setShortcut(QKeySequence("Ctrl+P"))
        pip_shortcut.triggered.connect(self.trigger_global_pip)
        self.addAction(pip_shortcut)

        self.macro_manager = MacroManager()

        self.view = QWebEngineView(self)

        self.history_crypto = HistoryCrypto()
        self.perm_manager = PermissionsManager()
        self.history_cache = self.load_encrypted_history()

        self.profile_manager = ProfileManager()
        self.interceptor = SecurityInterceptor(self)
        self.study_manager = StudyManager(self.interceptor)

        self.profile = QWebEngineProfile("Profile", self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setHttpCacheMaximumSize(104857600)
        #self.profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "AppleWebKit/537.36 (KHTML, like Gecko)" "Chrome/120.0.0.0 Safari/537.36")
        self.profile.setUrlRequestInterceptor(self.interceptor)
        #self.profile.downloadRequested.connect(self.handle_download)
        self.profile.setPersistentStoragePath(os.path.abspath("storage"))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.setMovable(True)
        
        self.add_tab_btn = QToolButton()
        self.add_tab_btn.setText(" ＋ ") # Используем полноширинный плюс для лучшего вида
        self.add_tab_btn.setToolTip("Новая вкладка (Ctrl+T)")
        self.add_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor) # Меняем курсор при наведении
        self.add_tab_btn.clicked.connect(lambda: self.add_new_tab(QUrl(self.config["homepage"]), "Новая вкладка"))
        self.tabs.setCornerWidget(self.add_tab_btn, Qt.Corner.TopLeftCorner)

        self.setCentralWidget(self.tabs)

        # Порядок создания панелей сверху вниз
        self.create_nav_bar()
        self.create_bookmarks_bar()
        self.create_progress_bar() # Линия под закладками

        self.download_list = []

        self.setup_shortcuts()
        self.setup_sidebar()
        self.add_new_tab(QUrl(self.config["homepage"]), "Запуск")

        self.settings_bridge = SettingsBridge(self)
        custom_qss = self.config.get("custom_qss", "")
        if custom_qss:
            QApplication.instance().setStyleSheet(custom_qss)
        else:
            theme_path = self.config.get("theme_path")
            if theme_path and os.path.exists(theme_path):
                self.apply_theme(theme_path)

    def trigger_global_pip(self):
        current_view = self.tabs.currentWidget()
        if current_view:
            current_view.page().runJavaScript("""const v = document.querySelector('video'); if(v) v.requestPictureInPicture()""")

    def create_nav_bar(self):
        nav = QToolBar("Navigation")
        nav.setObjectName("Navigation")
        nav.setMovable(False)
        self.addToolBar(nav)

        nav.addAction(QAction("⮜", self, triggered=lambda: self.tabs.currentWidget().back()))
        nav.addAction(QAction("⮞", self, triggered=lambda: self.tabs.currentWidget().forward()))
        nav.addAction(QAction("⟳", self, triggered=lambda: self.tabs.currentWidget().reload()))
        home_action = QAction("🏠", self)
        home_action.setToolTip("На главную")
        home_action.triggered.connect(self.go_home)
        nav.addAction(home_action)

        container_action = QAction("📦", self)
        container_action.setToolTip("Открыть вкладку в контейнере")
        container_action.triggered.connect(self.open_container_tab)
        nav.addAction(container_action)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Введите поисковый запрос или URL...") # <-- Добавлена подсказка для UX
        self.url_bar.setClearButtonEnabled(True) # <-- Добавляет встроенный крестик для быстрой очистки строки (фишка PyQt6)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav.addWidget(self.url_bar)

        # Spacer прижимает кнопку меню к правому краю
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        nav.addWidget(spacer)

        self.reader_action = QToolButton()# self.url_bar.addAction(QIcon(), QLineEdit.ActionPosition.TrailingPosition)
        self.reader_action.setText("📖")
        self.reader_action.setToolTip("Режим чтения")
        nav.addWidget(self.reader_action)

        # Кнопка статуса щита (AdBlock/Study) после URL бара
        self.shield_btn = QToolButton()
        self.shield_btn.setText("🛡")
        self.shield_btn.setToolTip("Статус защиты и блокировки")
        self.shield_btn.setStyleSheet("color: #a6e3a1; border: none;") # Зеленый по умолчанию
        nav.addWidget(self.shield_btn)

        self.profile_btn = QPushButton()
        self.profile_btn.setFixedSize(32, 32)
        self.profile_btn.setToolTip("Профиль пользователя")
    # Стиль для круглой аватарки
        self.profile_btn.setStyleSheet("""
            QPushButton {
            background-color: #333;
            border-radius: 16px;
            border: 2px solid #444;
        }
        QPushButton:hover { border-color: #0078d4; }
    """)
    
        self.profile_btn.clicked.connect(lambda: self.tabs.addTab(AccountSettingsPage(browser_app=self), "Настройки аккаунта"))
        nav.addWidget(self.profile_btn)

        self.menu_btn = QToolButton()
        self.menu_btn.setText(" ≡ ")
        menu = QMenu(self)
        menu.addAction("🕒 История", self.open_history)
        menu.addAction("🔑 Пароли", self.open_vault)
        menu.addSeparator()
        menu.addAction("⭐ Закладки", lambda: BookmarksDialog(self).exec())
        menu.addAction("⚙ Настройки", self.open_html_settings)
        
        self.menu_btn.setMenu(menu)
        self.menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        nav.addWidget(self.menu_btn)

        self.mic_indicator = QLabel("🎤")
        self.mic_indicator.setStyleSheet("color: red; font-size: 16px;")
        self.mic_indicator.hide()
        nav.addWidget(self.mic_indicator)

    def set_mic_indicator(self,state:bool):
        if state:
            self.mic_indicator.show()
        else:
            self.mic_indicator.hide()

    def toggle_study_mode(self):
        if not self.study_manager.is_active:
            self.study_manager.start_session(25)
            self.sidebar_widget.study_btn.setText("Остановить")
            self.sidebar_widget.study_btn.setObjectName("dangerBtn")
            self.shield_btn.setStyleSheet("color: #f38ba8;") # Красный - режим учебы
        else:
            self.study_manager.stop_session()
            self.sidebar_widget.study_btn.setText("Начать сессию")
            self.sidebar_widget.study_btn.setObjectName("primaryBtn")
            self.shield_btn.setStyleSheet("color: #a6e3a1;")
        # Принудительно обновляем стиль
        self.sidebar_widget.study_btn.setStyle(self.sidebar_widget.study_btn.style())

    def update_study_ui(self, seconds_left):
        mins, secs = divmod(seconds_left, 60)
        if hasattr(self.sidebar_widget, 'study_timer_label'):
            self.sidebar_widget.study_timer_label.setText(f"{mins:02d}:{secs:02d}")

    def run_selected_macro(self):
        current_item = self.sidebar_widget.macro_list.currentItem()
        if current_item:
            browser = self.tabs.currentWidget()
            if browser:
                self.macro_manager.execute_macro(current_item.text(), browser)

    def open_container_tab(self):
        dialog = ProfileSelectorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_profile_name()
            self.add_new_tab(QUrl("https://google.com"), f"[{name}]", container_name=name)

    def create_bookmarks_bar(self):
        self.bookmarks_bar = QToolBar("Bookmarks")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.bookmarks_bar)
        self.insertToolBarBreak(self.bookmarks_bar)
        self.load_bookmarks()

    def create_progress_bar(self):
        self.progress_toolbar = QToolBar("Loading")
        self.progress_toolbar.setMovable(False)
        self.progress_toolbar.setFixedHeight(4) 
        self.progress_toolbar.setContentsMargins(0, 0, 0, 0)
        self.progress_toolbar.setStyleSheet("QToolBar { border: none; padding: 0px; margin: 0px; spacing: 0px;}")
        
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.setRange(0,100)
        #self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.progress)

        self.progress_toolbar.addWidget(self.progress)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.progress_toolbar)
        self.insertToolBarBreak(self.progress_toolbar)
        self.progress_toolbar.hide()

    def setup_shortcuts(self):
        QAction(self, shortcut=QKeySequence("Ctrl+T"), triggered=lambda: self.add_new_tab(QUrl(self.config["homepage"]), "Новая вкладка")).setParent(self)
        QAction(self,shortcut=QKeySequence("Ctrl+Shift+N"), triggered=lambda: self.add_new_tab(QUrl(""), "Инкогнито", is_incognito=True)).setParent(self)
        QAction(self, shortcut=QKeySequence("Ctrl+W"), triggered=lambda: self.close_tab(self.tabs.currentIndex())).setParent(self)
        for act in self.findChildren(QAction): self.addAction(act)

    def add_new_tab(self, qurl, label, is_incognito=False,container_name="Default"):
        
        browser = QWebEngineView()
        browser.mic_active = False
        browser.current_progress = 100
        browser.loadStarted.connect(lambda b=browser: self.update_progress(0,b))

        target_url = ""
        if qurl and not qurl.isEmpty():
            target_url = qurl.toString()
        else:
            # Если qurl пустой, значит откроется либо домашняя страница, либо glide://home
            home_url = self.config.get("homepage", "").strip()
            target_url = home_url if home_url else "glide://home"

        # 2. Проверяем, является ли адрес внутренним (исправил опечатку is_internal)
        is_internal = any(target_url.startswith(s) for s in ["glide://", "about:", "qrc:"]) or target_url == ""

        if is_incognito:
            prof = QWebEngineProfile("", browser)
            prof.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
            prof.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
            prof.downloadRequested.connect(self.handle_download,Qt.ConnectionType.UniqueConnection)
            browser.setProperty("is_incognito", True)

        else:
            # Передаем self (BrowserApp) как parent_window
            prof = self.profile_manager.get_profile(container_name,self)
            custom_ua = self.config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "AppleWebKit/537.36 (KHTML, like Gecko)" "Chrome/139.0.0.0 Safari/537.36").strip()
            if custom_ua:
                prof.setHttpUserAgent(custom_ua)
            try:
                prof.downloadRequested.disconnect(self.handle_download)
            except TypeError:
                pass
            prof.downloadRequested.connect(self.handle_download)
            prof.setUrlRequestInterceptor(self.interceptor)

            
        page = CustomWebPage(prof, self, browser)

        page.featurePermissionRequested.connect(lambda url,feature,p=page:self.handle_permission(p,url,feature))

        if is_incognito:
            settings = page.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False)
        else:
            settings = page.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False)

        js_allowed = True if is_internal else self.config.get("js_enabled", True)
        img_allowed = True if is_internal else self.config.get("img_enabled", True)
         
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled,js_allowed)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages,img_allowed)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled,True)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        page.fullScreenRequested.connect(self.handle_fullscreen)
        page.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        browser.titleChanged.connect(lambda t, b=browser: self.tabs.setTabText(self.tabs.indexOf(b), (t[:20] if t.strip()else "Glide")))
        browser.setPage(page)
        
        browser.setUrl(qurl)
        if not qurl or qurl.isEmpty():
            home_url = self.config.get("homepage", "").strip()
            if not home_url:
                browser.setHtml(self.get_speed_dial_html(), QUrl("glide://home"))
            else:
                if not home_url.startswith(("http://", "https://")):
                    home_url = "https://" + home_url
                browser.setUrl(QUrl(home_url))
        else:
            browser.setUrl(qurl)
        i = self.tabs.addTab(browser, label)
        if is_incognito:
            self.tabs.tabBar().setTabTextColor(i,Qt.GlobalColor.magenta)
        self.tabs.setCurrentIndex(i)
        browser.page().recentlyAudibleChanged.connect(lambda audiable, b=browser: self.update_tab_audio_icon(b,audiable))
        

        browser.urlChanged.connect(lambda qurl, b=browser: self.update_url(qurl, b))
        browser.titleChanged.connect(lambda t, b=browser: self.tabs.setTabText(self.tabs.indexOf(b), t[:20]))
        browser.loadStarted.connect(lambda b=browser: self.update_progress(0,b))
        browser.loadProgress.connect(lambda p, b=browser: self.update_progress(p, b))
        browser.loadFinished.connect(lambda ok, b=browser: self.record_history(b) if ok else None)

        

        return browser

    def update_tab_audio_icon(self,browser,audible):
        index = self.tabs.indexOf(browser)
        if index != -1:
            if audible:
                self.tabs.setTabIcon(index, QIcon("icon/volume-on.png"))
            else:
                self.tabs.setTabIcon(index, QIcon())

    def add_speed_dial_item(self):
        name, ok1 = QInputDialog.getText(self, "Новая плитка", "Название сайта:")
        if not ok1 or not name.strip(): return

        url, ok2 = QInputDialog.getText(self, "Новая плитка", "URL (с https://):")
        if not ok2 or not url.strip(): return

        name, url = name.strip(), url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        tiles = load_json("speeddial.json", [])
        tiles.append({"name": name, "url": url})
        save_json("speeddial.json", tiles)

        # Обновляем текущую страницу, чтобы плитка появилась сразу
        curr = self.tabs.currentWidget()
        if curr:
            curr.setHtml(self.get_speed_dial_html(), QUrl("glide://home"))

    def get_speed_dial_html(self):
        tiles = load_json("speeddial.json", [
            {"name": "Google", "url": "https://google.com"},
            {"name": "YouTube", "url": "https://youtube.com"},
        ])

        tiles_html = ""
        for i, t in enumerate(tiles):
            tiles_html += f'''
            <div class="tile-wrapper">
                <a class="tile" href="{t["url"]}">
                    <div class="tile-top">
                        <div class="tile-icon">{t["name"][:1].upper()}</div>
                        <div class="tile-title">{t["name"]}</div>
                    </div>
                    <div class="tile-url">{t["url"]}</div>
                </a>
                <div class="tile-controls">
                    <a href="browser:edit-speed-dial?index={i}" class="control-btn edit-btn">✎</a>
                    <a href="browser:delete-speed-dial?index={i}" class="control-btn del-btn">×</a>
                </div>
            </div>
            '''

        add_tile_html = '''
        <a class="tile add-tile" href="browser:add-speed-dial">
            <div class="add-plus">+</div>
            <div class="tile-title">Добавить</div>
            <div class="tile-url">Новая быстрая вкладка</div>
        </a>
        '''

        # Считываем настройки для виджетов
        show_clock = self.config.get("show_clock", True)
        show_search = self.config.get("show_search", True)

        widgets_html = ""
        widgets_html += '<div id="greeting" class="greeting-text"></div>'

        if show_clock:
            widgets_html += '<div id="clock" class="clock-widget">00:00</div>'
        
        if show_search:
            widgets_html += '''
            <div class="search-widget">
                <input type="text" id="search-input" placeholder="Введите поисковый запрос или адрес сайта..." onkeydown="if(event.key === 'Enter') handleSearch()">
            </div>
            '''

        return f"""
        <html>
        <head>
            <title>Glide homepage</title>
            <style>
                * {{ box-sizing: border-box; }}
                body {{
                    margin: 0; min-height: 100vh; font-family: 'Segoe UI', sans-serif;
                    background: radial-gradient(circle at top, #1b1f2a 0%, #121212 55%, #0d0d0d 100%);
                    color: white; display: flex; flex-direction: column; align-items: center; padding: 48px 24px;
                }}

                /* Стиль для приведственной надписи*/
                .greeting-text {{
                    font-size: 24px;
                    opacity: 0.9;
                    margin-bottom: 10px;
                    height: 30px;
                    letter-spacing: 1px;
                    color: #cbd4f4;
                    text-align: center;
                }}
                
                /* Стили для виджетов (Часы и Поиск) */
                .widgets-container {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-bottom: 40px;
                    width: 100%;
                    max-width: 600px;
                }}
                
                .clock-widget {{
                    font-size: 72px;
                    font-weight: 200;
                    letter-spacing: 2px;
                    margin-bottom: 20px;
                    text-shadow: 0 4px 12px rgba(0,0,0,0.5);
                }}
                
                .search-widget {{
                    width: 100%;
                    position: relative;
                }}
                
                #search-input {{
                    width: 100%;
                    padding: 16px 24px;
                    border-radius: 30px;
                    border: 1px solid #333;
                    background: rgba(30, 30, 30, 0.8);
                    color: white;
                    font-size: 16px;
                    outline: none;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.3);
                    transition: all 0.3s ease;
                }}
                
                #search-input:focus {{
                    border-color: #5b8cff;
                    background: rgba(40, 40, 40, 0.95);
                    box-shadow: 0 8px 25px rgba(91, 140, 255, 0.2);
                }}

                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 18px; width: min(920px, 100%); }}
                
                .tile {{
                    display: flex; flex-direction: column; justify-content: space-between; min-height: 150px;
                    background: rgba(30, 30, 30, 0.92); padding: 18px; border-radius: 18px; text-decoration: none; color: white;
                    border: 1px solid #2f2f2f; transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
                    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.25); overflow: hidden; position: relative;
                }}
                .tile:hover {{ transform: translateY(-4px); border-color: #5b8cff; background: rgba(36, 36, 36, 0.98); box-shadow: 0 14px 30px rgba(0, 0, 0, 0.38); }}
                .tile-top {{ display: flex; align-items: center; gap: 12px; }}
                .tile-icon {{ width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; background: linear-gradient(135deg, #2c3e50, #3b82f6); font-weight: 700; font-size: 18px; flex-shrink: 0; }}
                .tile-title {{ font-size: 18px; font-weight: 700; line-height: 1.2; word-break: break-word; }}
                .tile-url {{ margin-top: 16px; color: #9aa4b2; font-size: 13px; word-break: break-all; line-height: 1.4; }}
                
                .tile-wrapper {{ position: relative; }}
                .tile-controls {{ position: absolute; top: 8px; right: 8px; display: flex; gap: 5px; opacity: 0; transition: opacity 0.2s; z-index: 10; }}
                .tile-wrapper:hover .tile-controls {{ opacity: 1; }}
                .control-btn {{ width: 24px; height: 24px; background: rgba(0,0,0,0.6); border-radius: 6px; color: white; text-decoration: none; display: grid; place-items: center; font-size: 14px; border: 1px solid #444; }}
                .edit-btn:hover {{ background: #0078d4; border-color: #0078d4; }}
                .del-btn:hover {{ background: #d32f2f; border-color: #d32f2f; }}

                .add-tile {{ border: 1px dashed #4b5563; background: rgba(24, 24, 24, 0.9); align-items: center; justify-content: center; text-align: center; }}
                .add-tile:hover {{ border-color: #7aa2ff; }}
                .add-plus {{ width: 54px; height: 54px; border-radius: 18px; display: grid; place-items: center; background: linear-gradient(135deg, #2563eb, #60a5fa); font-size: 34px; font-weight: 300; margin-bottom: 12px; box-shadow: 0 10px 24px rgba(37, 99, 235, 0.3); }}
                .section {{ width: min(920px, 100%); }}
            </style>
        </head>
        <body>
            <div class="widgets-container">
                {widgets_html}
            </div>

            <div class="section">
                <div class="grid">
                    {add_tile_html}
                    {tiles_html}
                </div>
            </div>

            <script>
                // Логика Часов
                function updateClock() {{
                    const clock = document.getElementById('clock');
                    if (clock) {{
                        const now = new Date();
                        const h = String(now.getHours()).padStart(2, '0');
                        const m = String(now.getMinutes()).padStart(2, '0');
                        clock.textContent = h + ':' + m;
                    }}
                }}

                // Логика Поиска
                function handleSearch() {{
                    const input = document.getElementById('search-input');
                    if (input && input.value.trim() !== "") {{
                        // Отправляем запрос в Python через специальную ссылку
                        window.location.href = "browser:search?query=" + encodeURIComponent(input.value);
                    }}
                }}
                
                function getGreetingByTime() {{
                    const hour = new Date().getHours();

                    if (hour >= 5 && hour < 12) return "Доброе утро!";
                    if (hour >= 12 && hour < 18) return "Добрый день!";
                    if (hour >= 18 && hour < 23) return "Добрый вечер!";
                    return "Доброй ночи!";
                }}

                function typeText(element,text,speed = 50,callback = null) {{
                    let i = 0;
                    element.textContent = "";
                    function typing() {{
                        if (i < text.length) {{
                            element.textContent += text[i];
                            i++;
                            setTimeout(typing,speed);
                        }} else if(callback) {{
                            callback();
                        }}
                    }}
                    typing();
                }}

                function deleteText(element, speed = 30, callback = null) {{
                    let text = element.textContent;
                    function deleting() {{
                        if (text.length > 0) {{
                            text = text.slice(0, -1);
                            element.textContent = text;
                            setTimeout(deleting,speed);
                        }} else if(callback) {{
                            callback();
                        }}
                    }}
                    deleting();
                }}

                window.addEventListener('load', () => {{
                    setInterval(updateClock, 1000);
                    updateClock();
                    const searchInput = document.getElementById('search-input');
                    if (searchInput) searchInput.focus();

                    const el = document.getElementById('greeting');
                    if (!el) return;

                    typeText(el, "Welcome to Glide!", 70, () => {{
                        setTimeout(() => {{
                            deleteText(el,30, ()=> {{
                                const greeting = getGreetingByTime();
                                typeText(el,greeting,70);
                            }});
                        }},4000);
                    }});
                }});
                
            </script>
        </body>
        </html>
        """

    def update_progress(self, p, b):
        b.current_progress = p
        if b == self.tabs.currentWidget():
            self.progress.setValue(p)
            if p >= 100:
                self.progress_toolbar.hide()
            else:
                self.progress_toolbar.show()

    def update_url(self, qurl, b=None):
        if b != self.tabs.currentWidget() and b: return
        if not self.url_bar.hasFocus():
            self.url_bar.setText(qurl.toString())
            self.url_bar.setCursorPosition(0)

    def navigate_to_url(self):
        txt = self.url_bar.text().strip()
        if not txt:
            return
        if txt == "glide://profile-settings":
            settings_widget = AccountSettingsPage(browser_app=self)
            index = self.tabs.addTab(settings_widget, "Настройки аккаунта")
            self.tabs.setCurrentIndex(index)
            return settings_widget
        elif txt == "glide://settings":
            self.open_html_settings()
            return
        elif txt == "glide://home":
            browser = QWebEngineView()
            browser.setHtml(self.get_speed_dial_html(), QUrl("glide://home"))
        
        if " " in txt or "." not in txt:
            search_engine = self.config.get("search_engine", "https://www.google.com/search?q=")
            final_url = search_engine + quote(txt)
        else:
            final_url = txt if txt.startswith(("http://", "https://")) else "https://" + txt

        current_browser = self.tabs.currentWidget()
        if current_browser:
            current_browser.setUrl(QUrl.fromUserInput(final_url))

    def open_html_settings(self):
        # Защита от создания дубликатов вкладок
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Настройки браузера":
                self.tabs.setCurrentIndex(i)
                return

        browser = QWebEngineView()
        
        # Инициализируем бридж только один раз
        if not hasattr(self, 'settings_bridge'):
            self.settings_bridge = SettingsBridge(self)
            
        from PyQt6.QtWebChannel import QWebChannel
        channel = QWebChannel(browser.page())
        channel.registerObject("settingsBridge", self.settings_bridge)
        browser.page().setWebChannel(channel)
        
        browser.titleChanged.connect(lambda t, b=browser: self.tabs.setTabText(self.tabs.indexOf(b), "Настройки браузера"))
        browser.urlChanged.connect(lambda qurl, b=browser: self.update_url(qurl, b))
        
        browser.setHtml(self.get_settings_html(), QUrl("glide://settings")) # Тот самый HTML из прошлого ответа
        
        i = self.tabs.addTab(browser, "Настройки браузера")
        self.tabs.setCurrentIndex(i)
        self.url_bar.setText("glide://settings")


    def get_settings_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                :root { --bg: #0f0f0f; --panel: #181818; --accent: #0078d4; --text: #e0e0e0; --border: #333; }
                body { margin: 0; font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
                
                /* Навигация слева */
                .sidebar { width: 220px; background: var(--panel); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
                .nav-item { padding: 15px 25px; cursor: pointer; color: #777; transition: 0.2s; font-size: 14px; border-left: 3px solid transparent; }
                .nav-item:hover { background: #222; color: #fff;  border-left-color: #0078ee; }
                .nav-item.active { background: #222; color: #fff; border-left-color: #00eeee; }

                /* Контент */
                .content { flex: 1; padding: 30px; overflow-y: auto; display: flex; flex-direction: column; }
                .tab-content { display: none; animation: fadeIn 0.3s; }
                .tab-content.active { display: block; }
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                
                h1 { font-size: 22px; margin: 0 0 25px 0; font-weight: 400; color: #fff; }
                .group { background: #1e1e1e; padding: 20px; border-radius: 8px; border: 1px solid #282828; margin-bottom: 20px; }
                label { display: block; margin-bottom: 10px; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
                
                input, select, textarea { 
                    width: 100%; padding: 12px; background: #121212; border: 1px solid var(--border);
                    color: #fff; border-radius: 6px; font-size: 14px; margin-bottom: 10px;
                }
                
                textarea {
                    resize: none; height: 100%; box-sizing: border-box; border: 1px solid #333; outline: none;
                }

                /* QSS РЕДАКТОР */
                #qss_editor {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    background: #000000;
                    color: #afafaf; /* Матричный зеленый */
                    height: 400px;
                    border: 1px solid #3e3e3e33;
                    padding: 15px;
                    font-size: 14px;
                    line-height: 1.6;
                    tab-size: 4;
                }

                .btn-row { display: flex; gap: 10px; margin-top: 20px; position: sticky; bottom: 0; background: var(--bg); padding: 15px 0; }
                .btn { padding: 10px 25px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: 0.2s; }
                .btn-save { background: var(--accent); color: white; }
                .btn-save:hover { background: #0086eb; }
                .btn-apply { background: #333; color: white; }
                .btn-apply:hover { background: #444;}
                .btn-secondary {  background: #ffffff; color: black; }
                .btn-secondary:hover {  background: #cccccc; }
                .btn-danger { background: #442222; color: #ff8888; }
                .btn-danger:hover {background: #553333;}
            </style>
        </head>
        <body>
            <div class="sidebar">
                <div style="padding: 25px; font-weight: bold; color: var(--accent); font-size: 20px;">GLIDE [DEV BUILD]</div>
                <div class="nav-item active" onclick="showTab('gen')">⚙ Основные</div>
                <div class="nav-item" onclick="showTab('app')">🎨 Внешний вид</div>
                <div class="nav-item" onclick="showTab('sec')">🛡 Безопасность</div>
                <div class="nav-item" onclick="showTab('site')">🖥️ Сайты</div>
                <div class="nav-item" onclick="showTab('sync')">🔄 Аккаунт и Sync</div>
                <div class="nav-item" onclick="showTab('eng')">🚀 Производительность</div>
                <div class="nav-item" onclick="showTab('ext')">🛠️ Расширения</div>
                <div class="nav-item" onclick="showTab('dev')">Разраб [DEV BUILD] </div>
            </div>

            <div class="content">
                <div id="gen" class="tab-content active">
                    <h1>Основные настройки</h1>
                    <div class="group">
                        <label>User-Agent Браузера</label>
                        <input type="text" id="user_agent" placeholder="По умолчанию: Glide/1.0">
                        <label>Поисковая система</label>
                        <select id="search_engine">
                            <option value="https://www.google.com/search?q=">Google</option>
                            <option value="https://yandex.ru/search/?text=">Yandex</option>
                            <option value="https://duckduckgo.com/?q=">DuckDuckGo</option>
                        </select>
                    </div>
                </div>

                <div id="app" class="tab-content">
                    <h1>Интерфейс и Стили</h1>
                    <div class="group">
                        <label>Библиотека стилей (themes/)</label>
                        <select id="theme_selector" onchange="loadSelectedTheme()">
                            <option value="">-- Выберите файл или создайте новый --</option>
                        </select>
                    </div>
                    <div class="group">
                        <label>Custom QSS Stylesheet</label>
                        <textarea id="qss_editor" spellcheck="false" placeholder="/* Твой стиль здесь... */"></textarea>
                        <button class="btn btn-apply" style="margin-top:10px;" onclick="applyQSS()">Предпросмотр стиля</button>
                        <button class="btn btn-secondary" style="margin-top:10px;" onclick="saveQssFile()">Сохранить в файл</button>
                    </div>
                </div>

                <div id="sec" class="tab-content">
                    <h1>Приватность</h1>
                    <div class="group">
                        <label>Adblock (Домены через запятую)</label>
                        <textarea id="adblock_list" style="height: 120px;" placeholder="google-analytics.com, ads.doubleclick.net"></textarea>
                    </div>
                    <div class="group">
                        <label>Разрешения контента (Глобально)</label>
                        <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;">
                            <label style="display: flex; align-items: center; gap: 10px; color: #fff; font-size: 14px; text-transform: none; margin: 0;">
                                <input type="checkbox" id="js_enabled" style="width: 18px; height: 18px; margin: 0;"> Включить JavaScript (Требуется перезагрузка вкладок)
                            </label>
                            <label style="display: flex; align-items: center; gap: 10px; color: #fff; font-size: 14px; text-transform: none; margin: 0;">
                                <input type="checkbox" id="img_enabled" style="width: 18px; height: 18px; margin: 0;"> Загружать изображения
                            </label>
                            <label style="display: flex; align-items: center; gap: 10px; color: #fff; font-size: 14px; text-transform: none; margin: 0;">
                                <input type="checkbox" id="cookies_enabled" style="width: 18px; height: 18px; margin: 0;"> Разрешить Cookies
                            </label>
                        </div>
                    </div>
                </div>

                <div id="sync" class="tab-content">
                    <h1>Облачная синхронизация</h1>
                    <div class="group">
                        <label>Сервер (URL)</label>
                        <input type="text" id="sync_url">
                        <label>E2EE Master Key (Шифрование)</label>
                        <input type="text" id="e2ee_key" placeholder="Твой секретный ключ для данных">
                        <p style="font-size:11px; color:#666;">Данные шифруются на клиенте перед отправкой.</p>
                    </div>
                </div>

                <div id="eng" class="tab-content">
                    <h1>Производительность</h1>
                    <div class="group">
                        <label>Графический API (Nvidia Fix)</label>
                        <select id="gpu_backend">
                            <option value="default">Авто (Рекомендуется)</option>
                            <option value="d3d11">DirectX 11 (Стабильно на Win)</option>
                            <option value="gl">OpenGL (Без шахматки)</option>
                        </select>
                        <p style="font-size:11px; color:#666;">Изменения вступят в силу после перезапуска.</p>
                    </div>
                </div>

                <div class="btn-row">
                    <button class="btn btn-save" onclick="saveAll()">Сохранить настройки</button>
                    <button class="btn btn-danger" onclick="bridge.clear_data()">Очистить всё</button>
                </div>
            </div>

            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
            
                var bridge;
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    bridge = channel.objects.settingsBridge;
                    loadSettings();
                    fetchThemes();
                });
                

                function loadSelectedTheme() {
                    const filename = document.getElementById('theme_selector').value;
                    if (!filename) {
                        document.getElementById('qss_editor').value = "";
                        return;
                    }
                    bridge.load_qss(filename, function(content) {
                        document.getElementById('qss_editor').value = content;
                    });
                }

                function fetchThemes() {
                    bridge.get_themes(function(response) {
                        const themes = JSON.parse(response);
                        const selector = document.getElementById('theme_selector');
                        selector.innerHTML = '<option value="">-- Новый файл --</option>';
                        themes.forEach(theme => {
                            const opt = document.createElement('option');
                            opt.value = theme;
                            opt.textContent = theme;
                            selector.appendChild(opt);
                        });
                    });
                }

                function saveQssFile() {
                    let filename = document.getElementById('theme_selector').value;
                    if (!filename) {
                        filename = prompt("Введите имя нового файла (например, custom.qss):");
                        if (!filename) return; // Отмена
                    }
                    const content = document.getElementById('qss_editor').value;
                    bridge.save_qss(filename, content);
                    alert("Стиль сохранен и применен навсегда.");
                    fetchThemes(); // Обновляем список файлов
                }

                function showTab(id) {
                    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                    document.getElementById(id).classList.add('active');
                    event.currentTarget.classList.add('active');
                }

                function loadSettings() {
                    bridge.get_settings(function(json) {
                        var s = JSON.parse(json);
                        document.getElementById('user_agent').value = s.user_agent || "";
                        document.getElementById('qss_editor').value = s.custom_qss || "";
                        document.getElementById('search_engine').value = s.search_engine || "";
                        document.getElementById('adblock_list').value = s.adblock || "";
                        document.getElementById('sync_url').value = s.sync_url || "";
                        document.getElementById('e2ee_key').value = s.e2ee_key || "";
                        document.getElementById('gpu_backend').value = s.gpu_backend || "default";
                        document.getElementById('js_enabled').checked = s.js_enabled !== false;
                        document.getElementById('img_enabled').checked = s.img_enabled !== false;
                        document.getElementById('cookies_enabled').checked = s.cookies_enabled !== false;
                    });
                }

                function applyQSS() {
                    bridge.apply_qss_now(document.getElementById('qss_editor').value);
                }

                function saveAll() {
                    var data = {
                        user_agent: document.getElementById('user_agent').value,
                        custom_qss: document.getElementById('qss_editor').value,
                        search_engine: document.getElementById('search_engine').value,
                        adblock: document.getElementById('adblock_list').value,
                        sync_url: document.getElementById('sync_url').value,
                        e2ee_key: document.getElementById('e2ee_key').value,
                        gpu_backend: document.getElementById('gpu_backend').value,
                        js_enabled: document.getElementById('js_enabled').checked,
                        img_enabled: document.getElementById('img_enabled').checked,
                        cookies_enabled: document.getElementById('cookies_enabled').checked,
                    };
                    bridge.save_settings(JSON.stringify(data));
                    alert("Настройки сохранены!");
                }
            </script>
        </body>
        </html>
        """


    def close_tab(self, i):
        if self.tabs.count() > 1:
            browser = self.tabs.widget(i)
            self.tabs.removeTab(i)
            
            try:
                browser.loadProgress.disconnect()
                browser.urlChanged.disconnect()
            except TypeError:
                pass
                
            browser.setPage(None) 
            browser.deleteLater() 
            
            # Собираем имена профилей, которые остались в открытых вкладках
            active_profiles = set()
            for index in range(self.tabs.count()):
                widget = self.tabs.widget(index)
                if hasattr(widget, 'page') and widget.page() is not None:
                    profile = widget.page().profile()
                    if hasattr(profile, 'storageName'):
                        active_profiles.add(profile.storageName())
            
            # Передаем список активных профилей в менеджер для очистки кэша
            if hasattr(self, 'profile_manager'):
                self.profile_manager.cleanup_unused_profiles(active_profiles)

        else:
            self.close()

    def load_bookmarks(self):
        self.bookmarks_bar.clear()
        add_act = QAction("⭐", self, triggered=self.add_bookmark)
        add_act.setToolTip("Новая закладка (текущая вкладка)")
        self.bookmarks_bar.addAction(add_act)
        self.bookmarks_bar.addSeparator()
        bms = load_json("bookmarks.json", {})
        for title, url in bms.items():
            act = QAction(title[:15], self)
            act.triggered.connect(lambda ch, u=url: self.tabs.currentWidget().setUrl(QUrl(u)))
            
            self.bookmarks_bar.addAction(act)
            button = self.bookmarks_bar.widgetForAction(act)
            if button:
                button.setProperty("url",url)
                button.installEventFilter(self)

    def add_bookmark(self):
        curr = self.tabs.currentWidget()
        if not curr: return
        bms = load_json("bookmarks.json", {})
        bms[self.tabs.tabText(self.tabs.currentIndex())] = curr.url().toString()
        save_json("bookmarks.json", bms)
        self.load_bookmarks()
    def go_home(self):
        curr = self.tabs.currentWidget()
        if not curr: return

        home_url = self.config.get("homepage", "").strip()

        # Если адрес не указан, показываем Speed Dial
        if not home_url or home_url.lower() == "about:blank":
            curr.setHtml(self.get_speed_dial_html(), QUrl("glide://home"))
            self.url_bar.setText("")
        else:
            # Если указан URL, проверяем наличие http и переходим
            if not home_url.startswith(("http://", "https://")):
                home_url = "https://" + home_url
            curr.setUrl(QUrl(home_url))
    def handle_download(self, download_item: QWebEngineDownloadRequest):
        # Сохраняем ссылку, чтобы объект не был удален сборщиком мусора
        self.download_list.append(download_item)
        
        # Определяем путь по умолчанию (папка Downloads в домашней директории)
        suggested_path = os.path.join(os.path.expanduser("~"), "Downloads", download_item.downloadFileName())
        
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", suggested_path)
        
        if not path:
            download_item.cancel()
            path = suggested_path
            return

        # Устанавливаем директорию и имя файла отдельно
        
        download_item.setDownloadDirectory(os.path.dirname(path))
        download_item.setDownloadFileName(os.path.basename(path))
        download_item.accept()
        

        # Автоматическое открытие боковой панели и переход на вкладку загрузок
        if not self.sidebar_dock.isVisible():
            self.sidebar_dock.show()
        
        # Индекс 4 соответствует setup_downloads_tab в вашем SidebarWidget
        self.sidebar_widget.tabs.setCurrentIndex(4)
        self.sidebar_widget.add_download_to_list(download_item)



    def open_history(self): HistoryDialog(self).exec()
    def open_vault(self): PasswordVaultDialog(self).exec()

    def delete_speed_dial_item(self, index):
        tiles = load_json("speeddial.json", [])
        if 0 <= index < len(tiles):
            confirm = QMessageBox.question(self, "Удаление", f"Удалить плитку '{tiles[index]['name']}'?")
            if confirm == QMessageBox.StandardButton.Yes:
                tiles.pop(index)
                save_json("speeddial.json", tiles)
                self.refresh_speed_dial()

    def edit_speed_dial_item(self, index):
        tiles = load_json("speeddial.json", [])
        if 0 <= index < len(tiles):
            old_name = tiles[index]['name']
            old_url = tiles[index]['url']
            
            name, ok1 = QInputDialog.getText(self, "Редактирование", "Название сайта:", text=old_name)
            if not ok1 or not name.strip(): return
            
            url, ok2 = QInputDialog.getText(self, "Редактирование", "URL:", text=old_url)
            if not ok2 or not url.strip(): return
            
            tiles[index] = {"name": name.strip(), "url": url.strip()}
            save_json("speeddial.json", tiles)
            self.refresh_speed_dial()

    def refresh_speed_dial(self):
        """Метод для мгновенного обновления страницы Speed Dial"""
        curr = self.tabs.currentWidget()
        # Проверяем, что мы находимся на пустой странице или главной
        if curr and (curr.url().toString() == "about:blank" or curr.url().isEmpty()):
            curr.setHtml(self.get_speed_dial_html(), QUrl("glide://home"))

    def setup_sidebar(self):
        self.sidebar_dock = QDockWidget("Модули", self)
        self.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.sidebar_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        # Подключаем новый комплексный виджет
        self.sidebar_widget = SidebarWidget(self)
        self.sidebar_dock.setWidget(self.sidebar_widget)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sidebar_dock)
        self.sidebar_dock.hide()
        
        self.sidebar_btn = QAction("🗔", self, triggered=self.toggle_sidebar)
        self.sidebar_btn.setToolTip("Боковая панель")
        self.findChild(QToolBar, "Navigation").addAction(self.sidebar_btn)

    def toggle_sidebar(self):
        if self.sidebar_dock.isVisible():
            self.fade_hide_progress_bar()

        else:
            self.sidebar_dock.show()
            self.fade_show_progress_bar()
    def handle_fullscreen(self,request):
        if request.toggleOn():
            request.accept()
            self._old_state = self.saveState()
            self._old_geometry = self.saveGeometry()
            for tb in self.findChildren(QToolBar):
                tb.hide()
            self.tabs.tabBar().hide()
            self.showFullScreen()
        else:
            request.accept()
            for tb in self.findChildren(QToolBar):
                tb.show()
            self.tabs.tabBar().show()
            self.showNormal()
            self.restoreGeometry(self._old_geometry)
            self.restoreState(self._old_state)
    def handle_permission(self, page, url, feature):
        host = url.host()
        feature_str = str(feature)
        
        # Проверяем сохраненные разрешения
        saved_perm = self.perm_manager.get_permission(host, feature_str)
        if saved_perm is not None:
            policy = QWebEnginePage.PermissionPolicy.PermissionGrantedByUser if saved_perm else QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            page.setFeaturePermission(url, feature, policy)
            if saved_perm and feature in (QWebEnginePage.Feature.MediaAudioCapture, QWebEnginePage.Feature.MediaAudioVideoCapture):
                self.set_mic_indicator(True)
            return

        features_map = {
            QWebEnginePage.Feature.MediaAudioCapture: "микрофону",
            QWebEnginePage.Feature.MediaVideoCapture: "камере",
            QWebEnginePage.Feature.MediaAudioVideoCapture: "камере и микрофону",
            QWebEnginePage.Feature.Geolocation: "геолокации",
        }
        feature_name = features_map.get(feature, "системным функциям")

        msg = QMessageBox(self)
        msg.setWindowTitle("Запрос разрешений")
        msg.setText(f"Сайт <b>{host}</b> запрашивает доступ к {feature_name}.")
        
        allow_btn = msg.addButton("Разрешить", QMessageBox.ButtonRole.AcceptRole)
        deny_btn = msg.addButton("Запретить", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        granted = msg.clickedButton() == allow_btn
        self.perm_manager.set_permission(host, feature_str, granted) # Сохраняем выбор

        policy = QWebEnginePage.PermissionPolicy.PermissionGrantedByUser if granted else QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
        page.setFeaturePermission(url, feature, policy)
        
        if granted and feature in (QWebEnginePage.Feature.MediaAudioCapture, QWebEnginePage.Feature.MediaAudioVideoCapture):
            self.set_mic_indicator(True)
    def on_tab_changed(self,index):
        current_browser = self.tabs.widget(index)
        if current_browser:
            self.update_url(current_browser.url(),current_browser)
            self.set_mic_indicator(getattr(current_browser,'mic_active',False))
            nav_bar = self.findChild(QToolBar, "Navigation")
            is_incognito = current_browser.property("is_incognito") == True
            if nav_bar.property("incognito") != is_incognito:
                nav_bar.setProperty("incognito", is_incognito)
                nav_bar.style().unpolish(nav_bar)
                nav_bar.style().polish(nav_bar)
            
            progress = getattr(current_browser,'current_progress',100)
            if progress < 100:
                self.progress.setValue(progress)
                self.progress.show()
            else:
                self.progress.hide()
    def load_encrypted_history(self):
        if not os.path.exists("history.enc"): return []
        try:
            with open("history.enc", "rb") as f:
                decrypted = self.history_crypto.decrypt(f.read())
                return json.loads(decrypted)
        except Exception as e:
            print(f"Ошибка чтения истории: {e}")
            return []

    def save_encrypted_history(self):
        try:
            data = json.dumps(self.history_cache)
            encrypted = self.history_crypto.encrypt(data)
            with open("history.enc", "wb") as f:
                f.write(encrypted)
        except Exception as e:
            print(f"Ошибка сохранения истории: {e}")

    # Заменяем старый record_history
    def record_history(self, browser):
        url = browser.url().toString()
        title = browser.title()
        if not url.startswith("http"): return
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.history_cache or self.history_cache[-1]["url"] != url:
            self.history_cache.append({"time": now, "title": title, "url": url})
            if len(self.history_cache) > 1000: 
                self.history_cache.pop(0)
            self.save_encrypted_history() # Можно вынести в closeEvent для лучшей производительности

    def show_https_warning(self, browser, target_url, host):
        html = f"""
        <html><body style="background:#121212;color:white;font-family:sans-serif;text-align:center;padding:50px;">
            <h1 style="color:#d32f2f;">Подключение не защищено</h1>
            <p>Вы пытаетесь перейти на <b>{host}</b> по незащищенному протоколу HTTP.</p>
            <div style="margin-top:30px;">
                <button onclick="window.location.href='browser:trust-http?host={host}&url={quote(target_url)}'" 
                        style="background:#333;color:white;border:none;padding:10px 20px;cursor:pointer;border-radius:5px;">
                    Я понимаю риск. Довериться сайту
                </button>
            </div>
        </body></html>
        """
        browser.setHtml(html)

    def toggle_reader_mode(self):
        curr_browser = self.tabs.currentWidget()
        if not curr_browser: return

        # Скрипт скрывает боковые панели, шапки, рекламу, но оставляет основной контент
        js_code = """
        (function() {
            if (document.getElementById('glide-reader-mode-css')) {
                document.getElementById('glide-reader-mode-css').remove();
                return; // Выключение
            }
            let style = document.createElement('style');
            style.id = 'glide-reader-mode-css';
            style.innerHTML = `
                header, footer, nav, aside, .ad, .advertisement, .sidebar, [class*="banner"], [id*="cookie"] { display: none !important; }
                body { max-width: 800px !important; margin: 0 auto !important; padding: 40px 20px !important; 
                       font-size: 18px !important; line-height: 1.6 !important; 
                       background-color: #121212 !important; color: #e0e0e0 !important; }
                img, iframe, video { max-width: 100% !important; height: auto !important; border-radius: 8px; }
                a { color: #89b4fa !important; }
            `;
            document.head.appendChild(style);
        })();
        """
        curr_browser.page().runJavaScript(js_code)
    
    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.MiddleButton:
                url_value = obj.property("url")
                if url_value:
                    self.add_new_tab(QUrl(url_value), "Новая вкладка")
                    return True
        return super().eventFilter(obj,event)



    def save_download_to_history(self, download_item):
        """Сохраняет информацию о загрузке на диск."""
        download_data = {
            "id": download_item.id(),
            "url": download_item.url().toString(),
            "downloadDirectory": download_item.downloadDirectory(),
            "downloadFileName": download_item.downloadFileName(),
            "state": download_item.state(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
        history = []
        if os.path.exists(DOWNLOADS_FILE):
            try:
                with open(DOWNLOADS_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                history = []
            
        history.append(download_data)
    
        with open(DOWNLOADS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def _on_download_state_changed(self, state, download_item):
        """Обработчик завершения или отмены загрузки."""
    # QWebEngineDownloadRequest.DownloadState.DownloadCompleted = 2
    # QWebEngineDownloadRequest.DownloadState.DownloadCancelled = 3
        if state in (2, 3): 
            self.save_download_to_history(download_item)
        
        # КРИТИЧНО ДЛЯ ПАМЯТИ: Удаляем объект из списка, позволяя сборщику мусора очистить ОЗУ
            if download_item in self.download_list:
                self.download_list.remove(download_item)
                download_item.deleteLater()

    def fade_show_progress_bar(self):
        self.opcity_effect = QGraphicsOpacityEffect(self.sidebar_dock)
        self.sidebar_dock.setGraphicsEffect(self.opcity_effect)
        self.animation = QPropertyAnimation(self.opcity_effect, b"opacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()
    def fade_hide_progress_bar(self):
        self.opcity_effect = QGraphicsOpacityEffect(self.sidebar_dock)
        self.sidebar_dock.setGraphicsEffect(self.opcity_effect)
        self.animation = QPropertyAnimation(self.opcity_effect, b"opacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.sidebar_dock.hide)
        self.animation.start()
    def apply_theme(self,theme_path):
        try:
            if os.path.exists(theme_path):
                with open(theme_path, "r", encoding="utf-8") as f:
                    style = f.read()
                    QApplication.instance().setStyleSheet(style)
                self.config["theme_path"] = theme_path
                save_json(SETTINGS_FILE, self.config)
                #self.apply_settings()
            else:
                print(f"Файл не найден {theme_path}")
        except Exception as e:
            print(f"Ошибка при загрузке пользовательского QSS: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        /* Основные окна и текст */
        QMainWindow, QDialog { background-color: #121212; color: #ffffff; }
        QLabel { color: #ffffff; } /* Исправление 2: белый текст в настройках */
        
        /* Панели инструментов */
        QToolBar { background-color: #181818; border: none; padding: 6px; spacing: 8px; }
        QToolBar::separator { background-color: #333; width: 1px; margin: 4px 10px; }
        QToolBar[incognito="true"] { background-color: #2b0044; }
        QToolBar[incognito="true"] QLineEdit { background-color: #1a0029; border: 1px solid #6b21a8; }
        QToolBar[incognito="true"] QLineEdit:focus { border: 1px solid #a855f7; background-color: #2b0044; }
        
        /* Адресная строка */
        QLineEdit { 
            background-color: #202020; color: #e0e0e0; 
            border-radius: 14px; padding: 6px 14px; 
            border: 1px solid #333; font-size: 13px;
        }
        QLineEdit:focus { border: 1px solid #0078d4; background-color: #252525; }
        
        /* Выпадающие списки (Исправление 3: цвета ComboBox) */
        QComboBox { background: #202020; color: white; border: 1px solid #333; padding: 6px; border-radius: 4px; }
        QComboBox QAbstractItemView { background-color: #202020; color: #ffffff; selection-background-color: #0078d4; }
        
        /* Вкладки */
        QTabWidget::pane { border: none; background: #121212; border-top: 1px solid #333; }
        QTabWidget#sidebarTabs QTabBar::tab {min-width: 40px; max-width: 40px; height: 40px; padding: 0px; margin-bottom: 2px; border-radius: 4px; background: #1e1e1e;}
        QTabWidget#sidebarTabs QTabBar::tab:selected {background: #3a3a3a; border-left: 2px solid #00eeee; border-top: none;}

        QTabWidget#sidebarTabs QTabBar::tab:hover {background-color: #1a1a1a; border-left: 2px solid #0078ee; border-top: none;}   
                    
        QTabBar::tab { 
            background: #1e1e1e; color: #888; 
            padding: 8px 16px; border: none; 
            border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;
            min-width: 150px; max-width: 250px; margin-right: 2px;
            
        }
        QTabBar::tab:selected { background: #3a3a3a; color: #ffffff; border-top: 2px solid #00eeee; }
        QTabBar::tab:hover:!selected { background: #252525; border-top: 2px solid #0078ee}
        
        /* Кнопки навигации и меню */
        QToolButton { color: #cccccc; border: none; padding: 6px; border-radius: 6px; font-size: 16px; }
        QToolButton:hover { background-color: #333333; color: #ffffff; }
        QMenu { background-color: #1e1e1e; color: #ffffff; border: 1px solid #333; border-radius: 6px; padding: 4px 0px; }
        QMenu::item { padding: 6px 24px; }
        QMenu::item:selected { background-color: #0078d4; border-radius: 4px; margin: 0px 4px; }
                      
        /* Крестик закрытия вкладки (Исправление 4: вернул крестик) */
        QTabBar::close-button { subcontrol-position: right; width: 16px; height: 16px}
       /* QTabBar::close-button:hover { background: rgba(211,47,47,0.8); border-radius: 4px;} */
        
        /* Таблицы и кнопки */
        QTableWidget, QListWidget { background-color: #1e1e1e; color: #ddd; border: 1px solid #333; border-radius: 6px; gridline-color: #333; }
        QHeaderView::section { background-color: #252525; color: #fff; padding: 4px; border: none; border-bottom: 1px solid #333; }
        QPushButton { padding: 8px 16px; border-radius: 6px; background-color: #333; color: white; border: none; font-weight: bold; }
        QPushButton:hover { background-color: #444; }
        QPushButton#primaryBtn { background-color: #0078d4; }
        QPushButton#primaryBtn:hover { background-color: #0086eb; }
        QPushButton#dangerBtn { background-color: #d32f2f; }
        QPushButton#dangerBtn:hover { background-color: #f44336; }
        
        /* Прогресс-бар и Скроллбары */
        QProgressBar { background-color: transparent; border: none; }
        QProgressBar::chunk { background-color: #0078d4; border-radius: 1px; }
        QScrollBar:vertical { background: #121212; width: 12px; margin: 0px; }
        QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 6px; margin: 2px; }
        QScrollBar::handle:vertical:hover { background: #555; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        
        /* Стили для страницы аккаунта */
/* Контейнер боковой панели аккаунта */
#AccountSidebar {
    background-color: #181818; /* Цвет панели --panel из HTML-настроек */
    border: none;
    border-right: 1px solid #333;
    padding 0px;
    outline: none;
}

/* Настройка каждого пункта списка (вкладки) */
#AccountSidebar::item {
    padding: 15px 25px;
    color: #777;
    font-size: 14px;
    border-left: 3px solid transparent;
    margin: 0px;
    width: 100%;
}

/* Эффект при наведении (hover) */
#AccountSidebar::item:hover {
    background-color: #222222;
    color: #ffffff;
    border-left: 3px solid #0078ee; /* Синяя полоска при наведении */
}

/* Стиль активной (выбранной) вкладки (selected/active) */
#AccountSidebar::item:selected {
    background-color: #222222;
    color: #ffffff;
    border-left: 3px solid #00eeee; /* Бирюзовая полоска для активной вкладки */
}

/* Убираем пунктирную рамку фокуса */
#AccountSidebar::item:focus { 
    outline: none; 
}


                    

    """)
    window = BrowserApp()
    window.show()
    
    sys.exit(app.exec())
