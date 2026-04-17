import os
from PyQt6.QtWebEngineCore import QWebEngineProfile

class ProfileManager:
    def __init__(self, base_dir="glide_data/containers"):
        self.base_dir = os.path.abspath(base_dir)
        self.active_profiles = {}
        os.makedirs(self.base_dir, exist_ok=True)

    def get_profile(self, name: str, parent=None) -> QWebEngineProfile:
        """Возвращает кэшированный профиль или создает новый."""
        if name in self.active_profiles:
            return self.active_profiles[name]

        profile = QWebEngineProfile(name, parent)
        path = os.path.join(self.base_dir, name)
        
        profile.setPersistentStoragePath(path)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        self.active_profiles[name] = profile
        return profile
    
    def cleanup_unused_profiles(self, active_profiles_in_use):
        """
        Удаляет профили из оперативной памяти, если они больше не используются вкладками.
        active_profiles_in_use - множество (set) имен профилей, которые сейчас открыты.
        """
        profiles_to_remove = []
        for profile_name in list(self.active_profiles.keys()):
            # Базовый профиль (Off-the-Record или дефолтный) не удаляем
            if profile_name not in active_profiles_in_use and profile_name != "default":
                profiles_to_remove.append(profile_name)

        for profile_name in profiles_to_remove:
            profile = self.active_profiles.pop(profile_name)
            profile.deleteLater()