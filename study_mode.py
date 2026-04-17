import json
import os
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

class StudyManager(QObject):
    timer_tick = pyqtSignal(int) # Сигнал для обновления UI (остаток в секундах)
    session_finished = pyqtSignal() # Сигнал завершения Помодоро

    def __init__(self, interceptor):
        super().__init__()
        self.interceptor = interceptor
        self.is_active = False
        self.time_left = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        
        self.blocklist = self._load_blocklist()

    def _load_blocklist(self):
        path = "study_blocklist.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        # Дефолтный список отвлечений
        default_list = ["youtube.com", "vk.com", "instagram.com", "tiktok.com", "twitch.tv"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_list, f, indent=4)
        return default_list

    def start_session(self, minutes=25):
        self.time_left = minutes * 60
        self.is_active = True
        self.interceptor.study_mode_active = True
        self.interceptor.study_blocklist = self.blocklist
        self.timer.start(1000)

    def stop_session(self):
        self.is_active = False
        self.interceptor.study_mode_active = False
        self.timer.stop()

    def _tick(self):
        self.time_left -= 1
        self.timer_tick.emit(self.time_left)
        if self.time_left <= 0:
            self.stop_session()
            self.session_finished.emit()
