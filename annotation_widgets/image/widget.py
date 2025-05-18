
import json
import time
import tkinter as tk
from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk
from jinja2 import Environment, FileSystemLoader
from pynput.keyboard import Listener

from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from annotation_widgets.image.models import Label
from annotation_widgets.io import AbstractAnnotationIO
from annotation_widgets.logic import AbstractAnnotationLogic
from annotation_widgets.widget import AbstractAnnotationWidget
from annotation_widgets.models import CheckResult
from config import templates_path
from exceptions import handle_exception
from gui_utils import show_html_window
from models import ProjectData


class AbstractImageAnnotationWidget(AbstractAnnotationWidget):
    def __init__(self, root: tk.Tk, io: AbstractAnnotationIO, logic: AbstractAnnotationLogic, project_data: ProjectData):
        super().__init__(root, io, logic, project_data)

        self.pack(side="top", fill="both", expand=True)

        # Use grid layout within the container
        self.grid_rowconfigure(0, weight=1)  # AbstractAnnotationWidget row, make it expandable
        self.grid_columnconfigure(0, weight=1)  # Single column for simplicity
        self.grid_rowconfigure(1, weight=0, minsize=40) # container for StatusBar

        # Canvas
        self.canvas_view = CanvasView(self, root=self, logic=self.logic)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")  # Make CanvasView expand in all directions

        # Status bar
        self.set_up_status_bar()
        assert self.status_bar is not None
        self.status_bar.grid(row=1, column=0, sticky='ew')  # StatusBar at the bottom, expanding horizontally

    def show_classes(self):

        data = [
            {
                "name": l.name,
                "type": l.type,
                "color": l.color,
                "hotkey": l.hotkey,
            }
            for l in Label.get_figure_labels()
        ]

        # Add keypoints color
        added_kp_names = set()
        for l in Label.get_figure_labels():
            attributes = l.attributes
            if attributes is None:
                continue
            
            keypoint_info = json.loads(attributes).get("keypoint_info")
            if keypoint_info is None:
                continue

            for kp_name, kp_data in keypoint_info.items():
                if kp_name in added_kp_names:
                    continue
                data.append(
                    {
                        "name": kp_name,
                        "type": "KEYPOINT",
                        "color": kp_data["color"],
                        "hotkey": "",
                    }
                )
                added_kp_names.add(kp_name)

        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        show_html_window(root=self, title="Classes", html_content=html_content)

    def set_up_status_bar(self):
        raise NotImplementedError

    def schedule_update(self):
        self.canvas_view.update_frame = True

    def close(self):

        if self.status_bar is not None:
            self.status_bar.destroy()
            self.status_bar = None 

        super().close()

    def on_overwrite(self):
        """Steps after annotation being overwritten, specific for widget"""
        self.update_frame = True
        self.schedule_update()

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        handle_exception(exc_type, exc_value, exc_traceback)

    def check_before_completion(self) -> CheckResult:
        self.logic.save_item()
        self.logic.save_state()
        return CheckResult()


class CanvasView(tk.Canvas):

    def __init__(self, parent: tk.Tk, root: tk.Tk, logic: AbstractImageAnnotationLogic):
        super().__init__(parent, bg="black")

        self.logic = logic

        self.parent=root

        self.scale_factor = 1.0
        self.x0, self.y0 = 0, 0

        # For calculating panning delta
        self.click_win_x, self.click_win_y = 0, 0
        self.start_x0, self.start_y0 = 0, 0
        self.panning = False

        self.update_frame = True

        self.fit_at_img_change = True

        self.last_key_press_time = time.time()
        self.min_time_between_frame_change = 0.1

        self.bind("<Button-1>", self.scale_event_wrapper(self.handle_left_mouse_press))
        self.bind("<Button-3>", self.handle_right_mouse_press)

        self.bind("<B1-Motion>", self.scale_event_wrapper(self.handle_mouse_move))
        self.bind("<B3-Motion>", self.handle_right_mouse_motion)

        self.bind("<Motion>", self.scale_event_wrapper(self.handle_mouse_hover))

        self.bind("<ButtonRelease-1>", self.scale_event_wrapper(self.handle_left_mouse_release))
        self.bind("<ButtonRelease-3>", self.scale_event_wrapper(self.handle_right_mouse_release))

        self.focus_set() # Set focus to the annotation_widget to receive keyboard events 

        self.bind("<Key>", self.handle_key_press) # For triggering methods by tkinter keyboard events

        self.bind("<MouseWheel>", self.on_mouse_wheel)  # For Windows
        self.bind("<Button-4>", self.on_mouse_wheel)  # For Unix/Linux, Zoom in
        self.bind("<Button-5>", self.on_mouse_wheel)  # For Unix/Linux, Zoom out

        self.bind("<Configure>", self.on_resize)

        self.bind("<space>", self.handle_space)
        self.bind("<Escape>", self.handle_esc)

        # Bindings for Shift press and release
        self.bind("<Shift_L>", self.on_shift_press)
        self.bind("<Shift_R>", self.on_shift_press)

        # Use timing mechanism to monitor if "A" key is held down
        self.last_a_press_time = 0
        self.a_held_down = False
        self.keyboard_events_interval = 0.1
        self.bind("<KeyPress-a>", self.handle_key_a_press)
        self.bind("<KeyPress-A>", self.handle_key_a_press)
        self.bind("<KeyRelease-a>", self.handle_key_a_release)
        self.bind("<KeyRelease-A>", self.handle_key_a_release)

        self.close_callback = None

        self.last_key_event = None
        self.any_key_pressed = False
        self.current_pressed_key = None

        # Start listening to the keyboard
        self.listener = Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.listener.start()

        self.logic.update_canvas()

    def on_key_press(self, key):
        self.any_key_pressed = True
        self.current_pressed_key = None
        try:
            if hasattr(key, 'char') and key.char:
                self.current_pressed_key = str(key.char).lower()
        except AttributeError:
            pass

    def on_key_release(self, key):
        self.any_key_pressed = False
        self.current_pressed_key = None
        self.last_key_event = None

    def on_shift_press(self, event):
        self.logic.on_shift_press()
        self.update_frame = True

    def handle_right_mouse_motion(self, event: tk.Event):
        if self.panning:
            win_cursor_x, win_cursor_y = event.x, event.y

            delta_x = (self.click_win_x - win_cursor_x) / self.scale_factor
            self.x0 = self.start_x0 + delta_x
            delta_y = (self.click_win_y - win_cursor_y) / self.scale_factor
            self.y0 = self.start_y0 + delta_y

            self.x0 = max(0, self.x0)
            self.y0 = max(0, self.y0)
            self.x0 = min(int(self.logic.orig_image.shape[1]*0.9), self.x0)
            self.y0 = min(int(self.logic.orig_image.shape[0]*0.9), self.y0)

        self.scale_event_wrapper(self.handle_mouse_move)(event)

    def handle_right_mouse_press(self, event: tk.Event):

        self.update_frame = True
        self.logic.update_time_counter("rmp")

        self.panning = True
        self.click_win_x, self.click_win_y = event.x, event.y
        self.start_x0, self.start_y0 = self.x0, self.y0

    def handle_left_mouse_press(self, event: tk.Event):
        self.logic.handle_left_mouse_press(event.x, event.y)
        self.update_frame = True
        self.logic.update_time_counter("lmp")

    def handle_mouse_move(self, event: tk.Event):
        self.logic.handle_mouse_move(event.x, event.y)
        self.update_frame = True

    def handle_left_mouse_release(self, event: tk.Event):
        self.logic.handle_left_mouse_release(event.x, event.y)
        self.update_frame = True

    def handle_right_mouse_release(self, event: tk.Event):
        self.update_frame = True
        self.panning = False

    def handle_mouse_hover(self, event: tk.Event):
        self.logic.handle_mouse_hover(event.x, event.y)
        self.update_frame = True

    def handle_space(self, event: tk.Event):
        self.logic.handle_space()
        self.update_frame = True

    def handle_esc(self, event: tk.Event):
        self.logic.handle_esc()
        self.update_frame = True

    def on_resize(self, event):
        self.update_canvas()
        self.fit_image()

    def handle_key_a_press(self, event: tk.Event):
        # TODO: Move handle_key_a_press, handle_key_a_release, check_key_a_pressed to ImageLabelingLogic
        self.last_a_press_time = time.time()
        if not self.a_held_down:

            self.logic.start_selecting_class()
            self.update_frame = True
            self.logic.update_time_counter("keyboard")

            self.a_held_down = True

    def handle_key_a_release(self, event: tk.Event):
        self.after(int(self.keyboard_events_interval * 1000), self.check_key_a_pressed)

    def check_key_a_pressed(self):
        if time.time() - self.last_a_press_time > self.keyboard_events_interval:
            self.logic.end_selecting_class()
            self.update_frame = True
            self.a_held_down = False

    def handle_key_press(self, event: tk.Event):
        if self.current_pressed_key is not None:
            if event.keysym.lower() == self.current_pressed_key:
                self.last_key_event = event
        elif self.any_key_pressed:
            self.last_key_event = event

    def process_last_key_press(self):
        if not self.any_key_pressed:
            return
        event = self.last_key_event
        if event is None:
            return

        ctrl_pressed = (event.state & 0x0004) != 0  # Control key mask
        cmd_pressed = (event.state & 0x0100) != 0  # Command key (macOS) mask

        if ctrl_pressed or cmd_pressed:  # Check if Ctrl or Command key is down
            if event.keysym.lower() == 'z':
                self.logic.undo()
            elif event.keysym.lower() == 'y':
                self.logic.redo()
            elif event.keysym.lower() == 'c':
                self.logic.copy()
            elif event.keysym.lower() == 'v':
                self.logic.paste()
            time.sleep(0.1) # Added to prevent too fast redo or paste

            self.update_frame = True
            self.logic.update_time_counter("keyboard")
            return

        if event.char.lower() == "w" or event.char.lower() == "p":
            if time.time() - self.last_key_press_time < self.min_time_between_frame_change:
                return
            self.logic.forward()
            if self.fit_at_img_change:
                self.fit_image()
            self.scale_event_wrapper(self.handle_mouse_hover)(event)
            self.update_frame = True

        elif event.char.lower() == "q" or event.char.lower() == "o":
            if time.time() - self.last_key_press_time < self.min_time_between_frame_change:
                return
            self.logic.backward()
            if self.fit_at_img_change:
                self.fit_image()
            self.scale_event_wrapper(self.handle_mouse_hover)(event)
            self.update_frame = True

        elif event.char.lower() == "f":
            self.fit_image()
        else:
            self.logic.handle_key(key=event.char.lower())

        self.last_key_press_time = time.time()
        self.logic.update_time_counter("keyboard")

        self.update_frame = True
        self.last_key_event = None

    def fit_image(self):
        """Fits image inside the annotation_widget and re-calculates scale_factor"""
        win_w=self.winfo_width()
        win_h=self.winfo_height()
        img_h, img_w, c = self.logic.orig_image.shape
        h_scale = win_h / img_h
        w_scale = win_w / img_w

        self.scale_factor = min(h_scale, w_scale)

        self.logic.scale_factor = self.scale_factor
        self.x0, self.y0 = 0, 0
        self.update_frame = True

    def scale_event_wrapper(self, handler):
        # Wrapper function to adjust event coordinates
        def wrapped_event(event):
            # Adjust the event coordinates based on the current scale
            scaled_x, scaled_y = self.xy_screen_to_image(event.x, event.y)
            img_h, img_w, _ = self.logic.orig_image.shape

            scaled_event = event
            scaled_event.x, scaled_event.y = max(0, min(scaled_x, img_w - 2)), max(0, min(scaled_y, img_h - 2))
            # Call the actual event handler with the scaled event
            return handler(scaled_event)
        return wrapped_event

    def on_mouse_wheel(self, event):

        # Coordinates in pixels on the image
        cursor_x, cursor_y = self.xy_screen_to_image(event.x, event.y)

        # Determine zoom direction
        scale_multiplier = 1.1
        if event.num == 5 or event.delta == -120:  # Zoom out
            self.scale_factor = max(self.scale_factor / scale_multiplier, 0.5)
        elif event.num == 4 or event.delta == 120:  # Zoom in
            self.scale_factor = min(self.scale_factor * scale_multiplier, 10)


        self.x0 = (cursor_x - (event.x / self.scale_factor))
        self.y0 = (cursor_y - (event.y / self.scale_factor))

        # Restrict x0y0 to be no less than 0 and no more than 2/3 of image
        self.x0 = max(0, self.x0)
        self.y0 = max(0, self.y0)
        self.x0 = min(int(self.logic.orig_image.shape[1]*0.9), self.x0)
        self.y0 = min(int(self.logic.orig_image.shape[0]*0.9), self.y0)

        self.logic.scale_factor = self.scale_factor

        self.logic.cursor_x, self.logic.cursor_y = self.xy_screen_to_image(event.x, event.y)

        self.update_frame = True

    def update_canvas(self):
        self.process_last_key_press()
        if self.update_frame:

            # Convert the OpenCV image to a format suitable for Tkinter
            self.logic.update_canvas()
            if self.logic.canvas is not None:
                cv_image = cv2.cvtColor(self.logic.canvas, cv2.COLOR_BGR2RGB)
                cv_image = self.get_image_zone(img=cv_image, x0=self.x0, y0=self.y0, scale=self.scale_factor)
                pil_image = Image.fromarray(cv_image)
                tk_image = ImageTk.PhotoImage(image=pil_image)

                # Clear the current contents of the canvas
                self.delete("all")

                # Add new image to the canvas
                self.create_image(0, 0, anchor="nw", image=tk_image)

                # Keep a reference to the image to prevent garbage collection
                self.tk_image = tk_image

                self.update_frame = False

        self.after(5, self.update_canvas)

    def xy_screen_to_image(self, x, y) -> Tuple[int, int]:
        """Transforms coordinates on the window to the coordinates on the image"""
        x_rel_unscaled, y_rel_unscaled = x / self.scale_factor, y / self.scale_factor
        x_img, y_img = x_rel_unscaled + self.x0, y_rel_unscaled + self.y0
        return int(x_img), int(y_img)

    def get_image_zone(self, img: np.ndarray, x0: int, y0: int, scale: float) -> np.ndarray:
        win_w=self.winfo_width()
        win_h=self.winfo_height()

        h_lim = int(win_h / scale + y0)
        w_lim = int(win_w / scale + x0)

        cropped = img[int(y0):h_lim, int(x0):w_lim]

        h, w, c = cropped.shape

        w_scaled = int(w * scale)
        h_scaled = int(h * scale)

        cropped = cv2.resize(cropped, (w_scaled, h_scaled), interpolation=cv2.INTER_AREA)
        return cropped

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        handle_exception(exc_type, exc_value, exc_traceback)
