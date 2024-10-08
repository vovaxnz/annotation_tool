import time
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk
from pynput.keyboard import Listener

from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from exceptions import handle_exception


class BaseCanvasView(tk.Canvas):
    """
    Class Contains base functionality of displaying Images in window.
    """
    def __init__(self, parent: tk.Tk, root: tk.Tk, logic: AbstractImageAnnotationLogic):
        super().__init__(parent, bg="black")

        self.logic = logic

        self.parent=root

        self.scale_factor = 1.0
        self.x0, self.y0 = 0, 0

        self.update_frame = True
        self.last_key_press_time = time.time()

        self.focus_set() # Set focus to the annotation_widget to receive keyboard events

        self.last_key_event = None
        self.any_key_pressed = False
        self.current_pressed_key = None

        # Start listening to the keyboard
        self.listener = Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.listener.start()

        self.bind("<Key>", self.handle_key_press) # For triggering methods by tkinter keyboard events
        self.bind("<Configure>", self.on_resize)

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

    def on_resize(self, event):
        self.update_canvas()
        self.fit_image()

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
