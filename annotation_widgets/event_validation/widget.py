import tkinter as tk

from annotation_widgets.widget import AbstractAnnotationWidget
from enums import EventViewMode
from models import ProjectData
from .gui import EventValidationStatusBar, EventValidationSideBar, BaseCanvasView
from .io import EventValidationIO
from .logic import EventValidationLogic


class EventValidationWidget(AbstractAnnotationWidget):
    def __init__(self, root: tk.Tk, io: EventValidationIO, logic: EventValidationLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

        self.pack(side="top", fill="both", expand=True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0, minsize=40)

        # Canvas
        self.canvas_view = BaseCanvasView(self, root=self, logic=self.logic)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")

        self.slider_widget = VideoFrameSlider(self, from_=0, to=100, callback=self.on_slider_change)
        self.slider_widget.grid(row=1, column=0, sticky="nsew")
        self.slider_widget.slider.config(variable=self.logic.current_frame_var)

        # Side Bar
        self.set_up_side_bar()
        assert self.side_bar is not None
        self.side_bar.grid(row=0, column=1, sticky="nsew")

        # Status Bar
        self.set_up_status_bar()
        assert self.status_bar is not None
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="nsew")

        # Event Hooks
        self.logic.on_item_change(self.update_sidebar_display)
        self.logic.on_view_mode_change(self.update_slider)
        self.update_sidebar_display()
        self.update_slider()

    def set_up_side_bar(self):
        self.side_bar = EventValidationSideBar(self, on_save_comment_callback=self.save_comment, on_save_answer_callback=self.save_answer)

    def set_up_status_bar(self):
        self.status_bar = EventValidationStatusBar(self, get_status_data_callback=lambda: self.logic.status_data)

    def update_sidebar_display(self):
        self.side_bar.update_display(
            comment=self.logic.comment,
            answers=self.logic.answers
        )

    def save_comment(self, new_comment):
        self.logic.update_comment(new_comment)

    def save_answer(self, question, selected_answer):
        self.logic.update_answer(question, selected_answer)

    def on_slider_change(self, val):
        frame_number = int(val)
        self.logic.load_video_frame(frame_number=frame_number)

    def update_slider(self):
        if self.logic.view_mode == EventViewMode.VIDEO.name:
            self.slider_widget.show()
            self.slider_widget.slider.config(to=self.logic.number_of_frames - 1)
            self.slider_widget.slider.set(self.logic.current_frame_number)
        else:
            self.slider_widget.hide()


class VideoFrameSlider(tk.Frame):
    def __init__(self, parent, from_, to, callback=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.callback = callback

        self.slider = tk.Scale(self, from_=from_, to=to, orient="horizontal", command=self.on_slider_change)
        self.slider.pack(side="left", fill="x", expand=True)

    def on_slider_change(self, value):
        if self.callback is not None:
            self.callback(value)

    def show(self):
        self.grid()

    def hide(self):
        self.grid_remove()
