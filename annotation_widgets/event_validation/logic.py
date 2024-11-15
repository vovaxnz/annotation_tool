import json
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from tkinter import messagebox
from typing import Callable, Optional

import cv2

from annotation_widgets.event_validation.models import Event
from annotation_widgets.event_validation.path_manager import EventValidationPathManager
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from enums import EventViewMode
from exceptions import MessageBoxException
from models import ProjectData, Value


@dataclass
class EventValidationStatusData:
    speed_per_hour: float
    item_id: int
    annotation_hours: float
    number_of_processed: int
    number_of_items: int
    view_mode: str
    number_of_frames: float
    current_frame_number: int


class EventValidationLogic(AbstractImageAnnotationLogic):
    def __init__(self, data_path: str, project_data: ProjectData):

        self.pm: EventValidationPathManager = self.get_path_manager(data_path)

        self._video_mode_only = True
        assert os.path.isdir(self.pm.videos_path)
        video_base_names = [item.split(".")[0] for item in os.listdir(self.pm.videos_path)]

        if os.path.isdir(self.pm.images_path) and len(os.listdir(self.pm.images_path)) > 0:
            self._video_mode_only = False
            image_base_names = [item.split(".")[0] for item in os.listdir(self.pm.images_path)]
            assert set(image_base_names) == set(video_base_names), "Number of 44 and videos are not the same"
 
        self.item_base_names = sorted(video_base_names)

        # View mode related logic init
        self.item_changed = False
        self.event: Event = None

        self.questions_map = json.loads(Value.get_value("fields"))  # Returns tree structure -> {"question_1": {"answer_1": "color_1", "answer_2": "color_2"...}}
        self.questions = list(self.questions_map.keys())

        self.comment = ""
        self.answers = OrderedDict((question, "") for question in self.questions)

        self.item_id = 0
        self.frames = []
        self.current_frame_number = 0

        # Callbacks init
        self._on_item_change: Callable = None
        self._on_view_mode_change: Callable = None
        self._on_frame_change: Callable = None

        # Set view mode
        self.view_mode: EventViewMode = None
        self.change_view_mode(EventViewMode.IMAGE)

        super().__init__(data_path=data_path, project_data=project_data)

    @property
    def number_of_frames(self) -> int:
        return len(self.frames)

    def change_view_mode(self, mode: EventViewMode):
        if self._video_mode_only:
            mode = EventViewMode.VIDEO
        self.view_mode = mode
        if self._on_view_mode_change is not None:
            self._on_view_mode_change()

    @staticmethod
    def _get_uid_from_name(name) -> Optional[str]:
        pattern = r'event-(?P<uid>[a-f0-9\-]+)\.[a-z0-9]+$'
        match = re.search(pattern, name)
        if match:
            return match.group('uid')

    @property
    def items_number(self) -> int:
        return len(self.item_base_names)

    @property
    def status_data(self) -> EventValidationStatusData:
        number_of_processed = len(self.processed_item_ids)
        return EventValidationStatusData(
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            item_id=self.item_id,
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_items=self.items_number,
            view_mode=self.view_mode.name,
            number_of_frames=self.number_of_frames,
            current_frame_number=self.current_frame_number,
        )

    @property
    def video_mode(self) -> bool:
        return self._video_mode_only or self.view_mode is EventViewMode.VIDEO

    def get_path_manager(self, project_id) -> EventValidationPathManager:
        return EventValidationPathManager(project_id)

    def load_item(self, next: bool = True):

        assert 0 <= self.item_id < self.items_number, f"The Image ID {self.item_id} is out of range of the images list: {self.items_number}"


        item_uid = self._get_uid_from_name(f"{self.item_base_names[self.item_id]}.mp4")
        if item_uid is None:
            return
        self.event = Event.get(uid=item_uid)
        assert self.event is not None, f"Event not found: {self.item_base_names[self.item_id]}, {item_uid}"
        self.answers = self.get_default_answers(event=self.event)
        self.comment = self.set_sidebar_comment(event=self.event)

        if self.video_mode:
            self.set_video_cap()
            self.load_video_frame()
        else:
            self.load_image()

        if self._on_item_change:
            self._on_item_change()

    def save_item(self):
        if self.item_changed:
            self.event.comment = self.comment
            self.event.custom_fields = json.dumps(list(self.answers.values()))
            self.event.save()

    def load_image(self):
        image_name = f"{self.item_base_names[self.item_id]}.jpg"
        orig_image = cv2.imread(os.path.join(self.pm.images_path, image_name))

        if orig_image is not None:
            self.orig_image = orig_image
            self.update_canvas()

    def set_video_cap(self, frames_limit: int = 1000):
        video_path = os.path.join(self.pm.videos_path, f"{self.item_base_names[self.item_id]}.mp4")
        assert video_path.endswith("mp4")

        self.frames.clear()

        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise MessageBoxException(f"Error opening video file {video_path}")

        counter = 0
        while True:
            ret, frame = self.cap.read()
            if ret:
                self.frames.append(frame)
                counter += 1
            else:
                break
            if counter > frames_limit:
                break

        # Set the current frame number to the middle of the video, because the event trigger is almost always in the middle of the video
        self.current_frame_number = int(len(self.frames) / 2) - 1 

        self.cap.release()

    def load_video_frame(self, frame_number: int = None) -> None:

        if frame_number is not None:
            # Don't load frame if frame number is out of video frame range
            if frame_number < 0 or frame_number > self.number_of_frames - 1:
                return
            self.current_frame_number = frame_number
        else:
            # Don't load frame if frame number is out of video frame range
            if self.current_frame_number >= self.number_of_frames - 1:
                return
            self.current_frame_number += 1

        self.orig_image = self.frames[self.current_frame_number]
        self.update_canvas()
        self.on_frame_change()

    def switch_item(self, item_id: int) -> None:
        if item_id > self.items_number - 1 or item_id < 0:
            return

        self.save_item()
        self.processed_item_ids.add(self.item_id)

        forward = item_id == self.item_id + 1
        self.item_id = item_id
        self.load_item(next=forward)
        self.save_state()

    def video_forward(self):
        self.load_video_frame()

    def video_backward(self):
        self.load_video_frame(frame_number=self.current_frame_number-1)

    def get_default_answers(self, event: Event) -> OrderedDict:
        stored_answers = event.validation_values.get("answers")
        if stored_answers:
            answers = OrderedDict(
                (question, stored_answers[idx] if idx < len(stored_answers) else "")
                for idx, question in enumerate(self.questions)
            )
        else:
            answers = OrderedDict((question, "") for question in self.questions)
        return answers

    @staticmethod
    def set_sidebar_comment(event: Event) -> str:
        return event.validation_values.get("comment")

    def set_on_item_change_callback(self, callback: Callable) -> None:
        self._on_item_change = callback

    def set_on_view_mode_change_callback(self, callback: Callable):
        self._on_view_mode_change = callback

    def set_on_frame_change_callback(self, callback: Callable):
        self._on_frame_change = callback

    def on_frame_change(self):
        if self._on_frame_change:
            self._on_frame_change()

    def update_comment(self, new_comment: str) -> None:
        self.comment = new_comment
        self.item_changed = True

    def update_answer(self, question: str, selected_answer: str) -> None:
        self.answers[question] = selected_answer
        self.item_changed = True

    def handle_key(self, key: str):
        if key.lower() == "q":
            self.backward()
        elif key.lower() == "w":
            self.forward()
        elif key.lower() == "a":  # Switch to IMAGE mode
            if self.video_mode:
                self.change_view_mode(EventViewMode.IMAGE)
                self.load_image()
        elif key.lower() == "s":  # Switch to VIDEO mode
            if not self.video_mode:
                self.change_view_mode(EventViewMode.VIDEO)
                self.load_video_frame(frame_number=self.current_frame_number)
        elif key.lower() == "z":
            if self.video_mode:
                self.video_backward()
        elif key.lower() == "x":
            if self.video_mode:
                self.video_forward()

        elif key.isdigit():
            if len(self.questions) >= int(key):
                question_idx = int(key) - 1
                question = self.questions[question_idx]
                self.cycle_answer(question)
                if self._on_item_change:
                    self._on_item_change()

    def cycle_answer(self, question: str) -> None:
        current_answer = self.answers[question]
        options = list(self.questions_map[question].keys())  # Get list of answers per selected question

        try:
            current_idx = options.index(current_answer)
        except ValueError:
            current_idx = -1

        next_idx = (current_idx + 1) % len(options)
        next_answer = options[next_idx]
        self.update_answer(question, next_answer)

    def update_canvas(self):
        self.canvas = self.orig_image
