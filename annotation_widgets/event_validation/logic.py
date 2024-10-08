import json
import os
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

import cv2

from annotation_widgets.event_validation.models import Event
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from enums import EventViewMode, EventValidationAnswerOptions
from exceptions import MessageBoxException
from models import ProjectData, Value


@dataclass
class EventValidationStatusData:
    speed_per_hour: float
    item_id: int
    annotation_hours: float
    number_of_processed: int
    number_of_items: int


class EventValidationLogic(AbstractImageAnnotationLogic):
    def __init__(self, data_path: str, project_data: ProjectData):

        self.view_mode = EventViewMode.IMAGE.name
        self.image_names = [item for item in sorted(os.listdir(os.path.join(data_path, "images")))]
        self.video_names = [item for item in sorted(os.listdir(os.path.join(data_path, "videos")))]
        self.questions = json.loads(Value.get_value("fields"))  # Preserve the original logic here

        assert len(self.image_names) == len(self.video_names)

        self.item_changed = False
        self.event: Event = None
        self.answers = []
        self.comment = ""
        self.answers = OrderedDict((question, "") for question in self.questions)
        self._on_item_change: Callable = None
        super().__init__(data_path=data_path, project_data=project_data)


    @property
    def items_number(self) -> int:
        return len(self.image_names)

    @property
    def status_data(self) -> EventValidationStatusData:
        number_of_processed = len(self.processed_item_ids)
        return EventValidationStatusData(
            speed_per_hour=round(number_of_processed / (self.duration_hours + 1e-7), 2),
            item_id=self.item_id,
            annotation_hours=round(self.duration_hours, 2),
            number_of_processed=number_of_processed,
            number_of_items=self.items_number,
        )

    @property
    def video_mode(self) -> bool:
        return self.view_mode == EventViewMode.VIDEO.name

    def load_item(self, next: bool = True):

        assert 0 <= self.item_id < len(self.image_names), f"The Image ID {self.item_id} is out of range of the images list: {len(self.image_names)}"

        self.view_mode = EventViewMode.IMAGE.name
        self.load_image()
        self.set_video_cap()
        self.event = Event.get(item_id=self.item_id)
        self.answers = self.get_default_answers(event=self.event)
        self.comment = self.set_sidebar_comment(event=self.event)

        if self._on_item_change:
            self._on_item_change()

    def save_item(self):
        if self.item_changed:
            self.event.comment = self.comment
            self.event.custom_fields = json.dumps(list(self.answers.values()))
            self.event.save()

    def load_image(self):
        image_name = self.image_names[self.item_id]
        orig_image = cv2.imread(os.path.join(self.pm.images_folder_path, image_name))

        if orig_image is not None:
            self.orig_image = orig_image
            self.canvas = orig_image

    def set_video_cap(self):
        video_path = os.path.join(self.pm.videos_folder_path, self.video_names[self.item_id])
        assert video_path.endswith("mp4")

        self.cap = cv2.VideoCapture(video_path)
        self.current_frame_number = 0
        self.number_of_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not self.cap.isOpened():
            raise MessageBoxException(f"Error opening video file {video_path}")

    def load_video_frame(self, frame_number: int):
        if frame_number > self.number_of_frames - 1 or frame_number < 0:
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        ret, frame = self.cap.read()
        if ret:
            self.orig_image = frame
            self.canvas = frame

        self.current_frame_number = frame_number

    def switch_mode(self):
        if not self.video_mode:
            self.view_mode = EventViewMode.VIDEO.name
            self.load_video_frame(frame_number=self.current_frame_number)
        else:
            self.view_mode = EventViewMode.IMAGE.name
            self.load_image()

    def switch_item(self, item_id: int):
        if item_id > self.items_number - 1 or item_id < 0:
            return

        self.save_item()
        self.processed_item_ids.add(self.item_id)

        forward = item_id == self.item_id + 1
        self.item_id = item_id
        self.load_item(next=forward)
        self.save_state()

    def video_forward(self):
        self.load_video_frame(frame_number=self.current_frame_number+1)

    def video_backward(self):
        self.load_video_frame(frame_number=self.current_frame_number-1)

    def get_default_answers(self, event: Event):
        stored_answers = event.sidebar_values.get("answers")
        if stored_answers:
            answers = OrderedDict(
                (question, stored_answers[idx] if idx < len(stored_answers) else "")
                for idx, question in enumerate(self.questions)
            )
        else:
            answers = OrderedDict((question, "") for question in self.questions)
        return answers

    @staticmethod
    def set_sidebar_comment(event: Event):
        return event.sidebar_values.get("comment")

    def on_item_change(self, callback: Callable):
        self._on_item_change = callback

    def update_comment(self, new_comment: str):
        self.comment = new_comment
        self.item_changed = True

    def update_answer(self, question: str, selected_answer: str):
        self.answers[question] = selected_answer
        self.item_changed = True

    def handle_key(self, key: str):
        if key.lower() == "q":
            self.backward()
        elif key.lower() == "w":
            self.forward()
        elif key.lower() == "e":  # TODO: To be confirmed
            pass
        elif key.lower() == "a":
            if self.video_mode:
                self.switch_mode()
        elif key.lower() == "s":
            if not self.video_mode:
                self.switch_mode()
        elif key.lower() == "z":
            if self.video_mode:
                self.video_backward()
        elif key.lower() == "x":
            if self.video_mode:
                self.video_forward()

        elif key.isdigit():
            question_idx = int(key) - 1
            question = self.questions[question_idx]
            self.cycle_answer(question)
            if self._on_item_change:
                self._on_item_change()

    def cycle_answer(self, question: str):
        current_answer = self.answers[question]
        options = EventValidationAnswerOptions.values()
        try:
            current_idx = options.index(current_answer)
        except ValueError:
            current_idx = -1

        next_idx = (current_idx + 1) % len(options)
        next_answer = options[next_idx]
        self.update_answer(question, next_answer)

    def update_canvas(self):
        pass
