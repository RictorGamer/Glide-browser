import json
import os

class MacroManager:
    def __init__(self, config_path="glide_data/macros.json"):
        self.config_path = config_path
        self.macros = self._load_macros()

    def _load_macros(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # Дефолтные макросы для примера
        default_macros = {
            "Dark Mode (Force)": "document.body.style.filter = 'invert(1) hue-rotate(180deg)';" ,
            "Extract Links": "console.log(Array.from(document.querySelectorAll('a')).map(a => a.href));",
            "Remove Ads (Quick)": "document.querySelectorAll('.ad, .ads, [id*=\"google_ads\"]').forEach(el => el.remove());"
        }
        self.save_macros(default_macros)
        return default_macros

    def save_macros(self, macros):
        self.macros = macros
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(macros, f, indent=4, ensure_ascii=False)

    def execute_macro(self, name, browser_view):
        if name in self.macros:
            code = self.macros[name]
            browser_view.page().runJavaScript(code)
