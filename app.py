import sys
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (QApplication, QMainWindow, QToolBar,
                             QLineEdit)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView

class ModernBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom Web Browser")
        self.setGeometry(100, 100, 1200, 800)

        # Инициализация движка
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.google.com"))
        self.setCentralWidget(self.browser)

        # Настройка панели навигации
        nav_bar = QToolBar("Навигация")
        nav_bar.setMovable(False)
        self.addToolBar(nav_bar)

        # Кнопка Назад
        back_btn = QAction("<", self)
        back_btn.triggered.connect(self.browser.back)
        nav_bar.addAction(back_btn)

        # Кнопка Вперед
        forward_btn = QAction(">", self)
        forward_btn.triggered.connect(self.browser.forward)
        nav_bar.addAction(forward_btn)

        # Кнопка Обновить
        reload_btn = QAction("Обновить", self)
        reload_btn.triggered.connect(self.browser.reload)
        nav_bar.addAction(reload_btn)

        # Умная адресная/поисковая строка
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Введите URL или поисковой запрос Google...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav_bar.addWidget(self.url_bar)

        # Обновление строки при переходе по ссылкам внутри страницы
        self.browser.urlChanged.connect(self.update_url)

        # Применение стилей (QSS) для современного внешнего вида
        self.setStyleSheet("""
            QMainWindow {
                background-color: #282a36;
            }
            QToolBar {
                background-color: #1e1e2e;
                border: none;
                padding: 8px;
                spacing: 12px;
            }
            QLineEdit {
                background-color: #44475a;
                color: #f8f8f2;
                border-radius: 18px;
                padding: 8px 20px;
                font-size: 14px;
                border: 2px solid transparent;
            }
            QLineEdit:focus {
                border: 2px solid #bd93f9;
                background-color: #282a36;
            }
            QToolButton {
                background-color: transparent;
                color: #f8f8f2;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 13px;
            }
            QToolButton:hover {
                background-color: #6272a4;
            }
            QToolButton:pressed {
                background-color: #bd93f9;
                color: #282a36;
            }
        """)

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
            
        # Простая эвристика: если есть точка и нет пробелов - это скорее всего URL
        if "." in text and " " not in text:
            if not text.startswith("http://") and not text.startswith("https://"):
                text = "https://" + text
            self.browser.setUrl(QUrl(text))
        else:
            # Иначе расцениваем как поисковой запрос в Google
            search_url = f"https://www.google.com/search?q={text.replace(' ', '+')}"
            self.browser.setUrl(QUrl(search_url))

    def update_url(self, q):
        self.url_bar.setText(q.toString())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernBrowser()
    window.show()
    sys.exit(app.exec())