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
        "bbox_line_width": {"type": "number", "value": 5, "min": 1, "max": 10, "step": 1},
        "bbox_point_size": {"type": "number", "value": 3, "min": 1, "max": 10, "step": 1},
        "mask_transparency": {"type": "number", "value": 0.5, "min": 0, "max": 1, "step": 0.1},
        "kp_radius": {"type": "number", "value": 5, "min": 1, "max": 10, "step": 1},
        "bbox_transparency": {"type": "number", "value": 0, "min": 0, "max": 1, "step": 0.1},
    }
}


class Settings:
    def __init__(self):
        self.json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "settings.json")
        self.data = DEFAULT_SETTINGS
        if not os.path.isfile(self.json_path):
            self.save_settings()
        self.load_settings()
        

    def load_settings(self):
        data = open_json(self.json_path)

        if not "general" in data:
            new_data = DEFAULT_SETTINGS
            new_data["general"]["token"]["value"] = data["token"] 
            new_data["general"]["api_url"]["value"] = data["api_url"] 
            new_data["general"]["file_url"]["value"] = data["file_url"] 
            new_data["general"]["data_dir"]["value"] = data["data_dir"] 
            data = new_data

        self.data = data


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
            self.load_settings()
            if result is None:
                raise MessageBoxException(f"Specify value of `{name}` in Project > Settings")
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






