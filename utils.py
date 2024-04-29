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


class HistoryBuffer:

    def __init__(self, length=10):
        self.history = list()
        self.length = length
        self.position = 0

    def add(self, value):
        if len(self.history) > 0 and value == self.history[-1]:
            return
        if len(self.history) > 0:
            self.history = self.history[:self.position + 1]
        self.history.append(value)
        self.history = self.history[-self.length:]
        self.position = len(self.history) - 1
    
    def get_previous(self):
        if len(self.history) == 0:
            return 
        if self.position - 1 >= 0:
            result = self.history[self.position - 1]
            if self.position > 0:
                self.position -= 1
            return result
    
    def get_next(self):
        if len(self.history) == 0:
            return 
        if self.position + 1 < len(self.history):
            result = self.history[self.position + 1]
            if self.position < self.length:
                self.position += 1
            return result
    
    def clear(self):
        self.history = list()
        self.position = 0