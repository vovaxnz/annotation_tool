import json
import os

def open_json(detections_file):
    with open(detections_file) as file:
        value = json.load(file)
    return value

def save_json(
    value,
    file_path,
):
    if os.path.islink(file_path):
        os.remove(file_path)
    if os.path.dirname(file_path) != "":
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as filename:
        json.dump(value, filename, indent=4)