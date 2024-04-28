import os
from typing import Any, Dict
from exceptions import MessageBoxException
from utils import open_json, save_json


templates_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

class Settings:
    def __init__(self):
        self.json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings.json")
        self.data: Dict[str, Any] = {
            "token": None,
            "api_url": None,
            "file_url": None,
            "data_dir": None,
        }
        if not os.path.isfile(self.json_path):
            self.save_settings()
        self.load_settings()

    def load_settings(self):
        self.data = open_json(self.json_path)

    def save_settings(self):
        save_json(value=self.data, file_path=self.json_path)
        os.chmod(self.json_path, 0o600)

    def get_setting(self, name: str):
        result = self.data.get(name)
        if result is None:
            self.load_settings()
            if result is None:
                raise MessageBoxException(f"Specify settings in Project > Settings")
        return result

    @property
    def has_empty(self):
        return any(value is None or value == "" for value in self.data.values())

    @property
    def token(self):
        return self.get_setting("token")
    
    @property
    def api_url(self):
        return self.get_setting("api_url")
    
    @property
    def file_url(self):
        return self.get_setting("file_url")
    
    @property
    def data_dir(self):
        return self.get_setting("data_dir")


settings = Settings()


class ColorBGR:
    red = (0, 0, 255)
    lime = (0, 255, 0)
    blue = (255, 0, 0)
    lightBlue = (170, 178, 32)
    yellow = (0, 255, 255)
    cyan = (255, 255, 0)
    magenta = (255, 0, 255)
    orange = (0, 140, 255)
    olive = (35, 142, 107)
    green = (0, 128, 0)
    purple = (211, 0, 148)
    pink = (180, 20, 255)
    black = (0, 0, 0)
    white = (255, 255, 255)
    gray = (192, 192, 192)
    brown = (19, 69, 139)
    color1 = (1, 1, 1)






