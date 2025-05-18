import os
from typing import Any, Dict
from exceptions import MessageBoxException
from utils import open_json, save_json


templates_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

DEFAULT_SETTINGS = {
    "general": {
        "token": {"type": "string", "value": None},
        "api_url": {"type": "string", "value": None},
        "file_url": {"type": "string", "value": None},
        "data_dir": {"type": "string", "value": None},
    },
    "interface": {
        "bbox_line_width": {"type": "number", "value": 3, "min": 1, "max": 10, "step": 1},
        "cursor_proximity_threshold": {"type": "number", "value": 3, "min": 1, "max": 10, "step": 1},
        "objects_opacity": {"type": "number", "value": 0.9, "min": 0, "max": 1, "step": 0.1},
        "color_fill_opacity": {"type": "number", "value": 0.1, "min": 0, "max": 1, "step": 0.1},
        "bbox_handler_size": {"type": "number", "value": 3, "min": 1, "max": 10, "step": 1},
        "keypoint_handler_size": {"type": "number", "value": 5, "min": 1, "max": 10, "step": 1},
    }
}




def update_dict_values(user_dict: Dict, default_dict: Dict) -> bool:
    """Updates default_dict with user_dict values if they not None"""
    updated = False
    for key, value in default_dict.items():
        if key in user_dict:
            if isinstance(value, dict):
                sub_updated = update_dict_values(user_dict=user_dict[key], default_dict=default_dict[key])
                if sub_updated:
                    updated = True
            else:
                if default_dict.get(key) != user_dict.get(key):
                    default_dict[key] = user_dict[key]
                    updated = True

    return updated


class Settings:
    def __init__(self):
        self.json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings.json")
        
        self.data = DEFAULT_SETTINGS
        updated = update_dict_values(
            user_dict=open_json(self.json_path) if os.path.isfile(self.json_path) else dict(), 
            default_dict=self.data
        )
        if updated:
            self.save_settings()

    def save_settings(self):
        save_json(value=self.data, file_path=self.json_path)
        os.chmod(self.json_path, 0o600)

    def get_setting(self, name: str):
        result = self.data.get(name)

        # If not found - search in nested dicts
        if result is None:
            for key, value in self.data.items():
                if isinstance(value, dict):
                    result = value.get(name)
                    if result is not None:
                        break
        
        # Take only value if setting contain other information
        if isinstance(result, dict):
            result = result["value"]
        
        if result is None:
            raise MessageBoxException(f"Specify value of `{name}` in Project > Settings. Your current settings: {self.data}")
        return result

    @property
    def has_empty(self):
        return any(value is None or value == "" for value in self.data.values())

    def __getattr__(self, name: str):
        
        if name in self.__dict__: # if the name is an instance attribute
            return self.__dict__[name]
        
        if name in dir(self.__class__): # if the name is a property method or a class attribute
            attr = getattr(self.__class__, name)
            if isinstance(attr, property):
                return attr.fget(self)
            else:
                return attr
            
        # for attributes not found in the instance or class attributes
        return self.get_setting(name)

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






