import os
import importlib.util
import logging

class ExtensionManager:
    def __init__(self, browser_app, ext_dir="extensions"):
        self.ext_dir = ext_dir
        self.browser_app = browser_app
        self.loaded_extensions = {}
        os.makedirs(self.ext_dir, exist_ok=True)

    def load_all(self):
        for filename in os.listdir(self.ext_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                self.load_extension(filename)

    def load_extension(self, filename):
        ext_name = filename[:-3]
        filepath = os.path.join(self.ext_dir, filename)
        
        try:
            spec = importlib.util.spec_from_file_location(ext_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Ожидаем, что в расширении есть класс Extension
            if hasattr(module, 'Extension'):
                ext_instance = module.Extension(self.browser_app)
                ext_instance.on_load()
                self.loaded_extensions[ext_name] = ext_instance
                logging.info(f"Расширение {ext_name} загружено.")
        except Exception as e:
            logging.error(f"Ошибка загрузки {ext_name}: {e}")

    def unload_extension(self, ext_name):
        if ext_name in self.loaded_extensions:
            self.loaded_extensions[ext_name].on_unload()
            del self.loaded_extensions[ext_name]
