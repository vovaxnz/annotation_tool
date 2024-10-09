from abc import ABC, abstractmethod
import json
import time

from models import ProjectData, Value
from path_manager import BasePathManager
from utils import get_datetime_str


class AbstractAnnotationLogic(ABC):

    def __init__(self, data_path: str, project_data: ProjectData):

        self.project_data: ProjectData = project_data

        self.tick_time = time.time()
        self.max_action_time_sec = 60
        self.item_id = 0 
        self.duration_hours = 0
        self.processed_item_ids: set = set()

        self.pm = self.get_path_manager(project_id=self.project_data.id)

        self.load_state()
        self.load_item(next=False)

    @property
    def items_number(self) -> int:
        raise NotImplementedError

    @property
    def status_data(self):
        raise NotImplementedError

    @abstractmethod
    def load_item(self, next: bool = True):
        raise NotImplementedError

    @abstractmethod
    def save_item(self):
        raise NotImplementedError

    def get_path_manager(self, project_id) -> BasePathManager:
        raise NotImplementedError

    def save_state(self):  # TODO: Save values as a batch
        Value.update_value("item_id", self.item_id)
        Value.update_value("duration_hours", self.duration_hours)
        Value.update_value("processed_item_ids", list(self.processed_item_ids))
        Value.update_value("annotation_stage", self.project_data.stage.name)

    def load_state(self):
        annotation_stage_name = Value.get_value("annotation_stage")
        if self.project_data.stage.name != annotation_stage_name: # If annotation stage is changed
            self.item_id = 0
            self.duration_hours = 0
            self.processed_item_ids = set()
            self.item_changed = True
        else:
            item_id = Value.get_value("item_id")
            self.item_id = int(item_id) if item_id is not None else self.item_id

            duration_hours = Value.get_value("duration_hours")
            self.duration_hours = float(duration_hours) if duration_hours is not None else self.duration_hours

            processed_item_ids = Value.get_value("processed_item_ids")
            self.processed_item_ids = set(json.loads(processed_item_ids)) if processed_item_ids is not None else self.processed_item_ids

            self.item_changed = False
        
        assert self.item_id < self.items_number, f"Incorrect item_id {self.item_id}. The number of items is {self.items_number}"

    def update_time_counter(self, message: str = None):
        with open(self.pm.statistics_path, 'a+') as file:
            file.write(f"{self.project_data.stage.name},{get_datetime_str()},{message}\n")
        curr_time = time.time()
        step_duration = min(curr_time - self.tick_time, self.max_action_time_sec)
        self.tick_time = curr_time
        self.duration_hours += step_duration / 3600

    @abstractmethod
    def switch_item(self, item_id: int):
        """Switch to image by id"""
        raise NotImplementedError

    def forward(self):
        self.switch_item(item_id=self.item_id+1)
        
    def backward(self):
        self.switch_item(item_id=self.item_id-1)

    def go_to_id(self, item_id: int):
        self.switch_item(item_id=item_id)

    def handle_left_mouse_press(self, x: int, y: int):
        pass

    def handle_mouse_move(self, x: int, y: int):
        pass

    def handle_mouse_hover(self, x: int, y: int):
        pass

    def handle_left_mouse_release(self, x: int, y: int):
        pass

    def handle_space(self):
        pass

    def handle_esc(self):
        pass

    def handle_key(self, key: str):
        pass

    def on_shift_press(self):
        pass
    
    def redo(self):
        pass

    def undo(self):
        pass
    
    def copy(self):
        pass

    def paste(self):
        pass
