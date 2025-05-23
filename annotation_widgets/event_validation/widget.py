import tkinter as tk

from annotation_widgets.event_validation.gui import (
    EventValidationStatusBar,
    EventValidationSideBar,
    BaseCanvasView,
    VideoFrameSlider,
)
from annotation_widgets.event_validation.io import EventValidationIO
from annotation_widgets.event_validation.logic import EventValidationLogic
from annotation_widgets.event_validation.models import Event
from annotation_widgets.models import CheckResult
from annotation_widgets.widget import AbstractAnnotationWidget
from enums import EventViewMode
from models import ProjectData


class EventValidationWidget(AbstractAnnotationWidget):
    def __init__(self, root: tk.Tk, io: EventValidationIO, logic: EventValidationLogic, project_data: ProjectData):
        self.logic: EventValidationLogic
        super().__init__(root, io, logic, project_data)

        self.pack(side="top", fill="both", expand=True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=40)

        # Canvas
        self.canvas_view = BaseCanvasView(self, root=self,
                                          on_update_canvas_callback=self.logic.update_canvas,
                                          on_handle_key_callback=self.logic.handle_key,
                                          on_update_time_counter_callback=self.logic.update_time_counter,
                                          on_get_orig_image_callback=lambda: self.logic.orig_image)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")

        # Slider Widget
        self.is_playing = False
        self.set_up_slider_widget()

        # Side Bar
        self.set_up_side_bar()
        assert self.side_bar is not None
        self.side_bar.grid(row=0, column=1, sticky="nsew")

        # Status Bar
        self.set_up_status_bar()
        assert self.status_bar is not None
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="nsew")

        # Event Hooks
        self.logic.set_on_item_change_callback(self.update_widgets_display)
        self.logic.set_on_view_mode_change_callback(self.update_slider)
        self.logic.set_on_frame_change_callback(self.update_slider_position)
        self.update_widgets_display()

        self.bind_all("<Button-1>", self.handle_left_mouse_press)
        self.bind_all("<Button-3>", self.handle_right_mouse_press)

    def handle_right_mouse_press(self, event: tk.Event):
        self.logic.update_time_counter("rmp")

    def handle_left_mouse_press(self, event: tk.Event):
        self.logic.update_time_counter("lmp")

    def set_up_side_bar(self):
        self.side_bar = EventValidationSideBar(self, on_save_comment_callback=self.save_comment, on_save_answer_callback=self.save_answer)

    def set_up_status_bar(self):
        self.status_bar = EventValidationStatusBar(self, get_status_data_callback=lambda: self.logic.status_data)

    def update_widgets_display(self):
        self.side_bar.update_display(
            comment=self.logic.comment,
            answers=self.logic.answers
        )
        self.update_slider()

    def save_comment(self, new_comment):
        self.logic.update_comment(new_comment)

    def save_answer(self, question, selected_answer):
        self.logic.update_answer(question, selected_answer)

    def set_up_slider_widget(self):
        self.slider_widget = VideoFrameSlider(self, from_=1, to=self.logic.number_of_frames,
                                              on_change_callback=self.on_slider_change,
                                              on_play_pause_callback=self.handle_play_pause,
                                              on_stop_callback=self.handle_stop)
        self.slider_widget.grid(row=1, column=0, sticky="nsew")

    def on_slider_change(self, val: int):
        frame_number = val - 1
        self.logic.load_video_frame(frame_number=frame_number)
        self.canvas_view.update_frame = True

    def update_slider(self):
        self.slider_widget.set_stop()
        if self.logic.view_mode is EventViewMode.VIDEO:
            self.slider_widget.show()
            self.slider_widget.slider.config(to=self.logic.number_of_frames)
            self.update_slider_position()
        else:
            self.slider_widget.hide()

    def update_slider_position(self):
        self.slider_widget.slider.set(self.ui_current_frame_number)

    def handle_play_pause(self):
        self.is_playing = not self.is_playing
        self.slider_widget.update_play_pause_button(self.is_playing)
        if self.is_playing:
            self.play_video()
        else:
            self.after_cancel(self.play_video)

    def handle_stop(self):
        self.is_playing = False
        self.slider_widget.update_play_pause_button(self.is_playing)
        self.slider_widget.slider.set(1)
        self.canvas_view.update_frame = True

    def play_video(self):
        if self.logic.current_frame_number >= self.logic.number_of_frames - 1:
            self.is_playing = False
            self.slider_widget.update_play_pause_button(self.is_playing)
            return

        if self.is_playing:
            self.logic.video_forward()
            self.update_slider_position()
            self.canvas_view.update_frame = True
            self.after(10, self.play_video)

    @property
    def ui_current_frame_number(self) -> int:
        return self.logic.current_frame_number + 1

    def on_overwrite(self):
        """Steps after annotation being overwritten, specific for widget"""
        self.update_widgets_display()

    def add_menu_items(self, root: tk.Tk):
        assert root.file_menu is not None
        root.file_menu.add_command(label="Download and overwrite annotations", command=self.overwrite_annotations)

    def close(self):
        # Unbind explicitly, because we use bind_all in constructor
        self.unbind_all("<Button-1>") 
        self.unbind_all("<Button-3>") 
        super().close()

    def check_before_completion(self) -> CheckResult:
        self.logic.save_item()
        self.logic.save_state()
        if unanswered_events := Event.get_unvalidated_event_ids():
            return CheckResult(
                ready_to_complete=False,
                message=f"Events № {unanswered_events} are not answered. Finish them to complete the project"
            )
        return CheckResult()
