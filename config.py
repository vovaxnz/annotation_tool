
from dataclasses import dataclass
import json
from typing import Dict

import numpy as np


@dataclass
class CamConfig:
    transform_s2v: Dict
    transform_v2s: Dict
    undistort: Dict

cam_config_path = "cam_config.json"

with open(cam_config_path) as file:
    cam_config_dict = json.load(file)

cam_configs: Dict[str, CamConfig] = {
    cam_name: CamConfig(
        transform_s2v=parameters["transform_s2v"],
        transform_v2s=parameters["transform_v2s"],
        undistort={key: np.array(value) for key, value in parameters["undistort"].items()},
    ) 
    for cam_name, parameters in cam_config_dict.items()
}

class ColorBGR:
    Red = (0, 0, 255)
    Lime = (0, 255, 0)
    Blue = (255, 0, 0)
    LightBlue = (170, 178, 32)
    Yellow = (0, 255, 255)
    Cyan = (255, 255, 0)
    Magenta = (255, 0, 255)
    Orange = (0, 140, 255)
    Olive = (35, 142, 107)
    Green = (0, 128, 0)
    Purple = (211, 0, 148)
    Pink = (180, 20, 255)
    Black = (0, 0, 0)
    White = (255, 255, 255)
    Gray = (192, 192, 192)
    Brown = (19, 69, 139)
    Color1 = (1, 1, 1)

POINT_COLORS = [
    ColorBGR.Red, # FL
    ColorBGR.Yellow, # FR
    ColorBGR.Cyan, # BR
    ColorBGR.Purple # BL
]


database_path = 'sqlite:///db.sqlite'