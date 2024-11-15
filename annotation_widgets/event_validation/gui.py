import json
import time
import tkinter as tk
from collections import OrderedDict
from collections.abc import Callable
from tkinter import font, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk
from pynput.keyboard import Listener

from annotation_widgets.event_validation.logic import EventValidationStatusData
from annotation_widgets.image.logic import AbstractImageAnnotationLogic
from enums import EventViewMode
from exceptions import handle_exception
from models import Value


class EventValidationStatusBar(tk.Frame):
    def __init__(self, parent, get_status_data_callback: Callable, **kw):
        super().__init__(parent, **kw)

        self.get_status_data = get_status_data_callback

        # Create labels within the status bar
        self.mode_label = tk.Label(self, bd=1)
        self.item_id_label = tk.Label(self, bd=1)
        self.speed_label = tk.Label(self, bd=1)
        self.processed_label = tk.Label(self, bd=1)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.duration_label = tk.Label(self, bd=1)

        # Video frame info label
        self.preview_mode_label = tk.Label(self, bd=1)

        # Initialize labels and separators
        self.initialize_labels_and_separators()

        # Bind the resize event
        self.bind("<Configure>", self.on_resize)

        self.update_status()

    def initialize_labels_and_separators(self):
        # Place each label and the progress bar in the grid
        self.mode_label.grid(row=0, column=0, sticky='ew', padx=15)
        sep1 = ttk.Separator(self, orient='vertical')
        sep1.grid(row=0, column=1, sticky='ns')

        self.item_id_label.grid(row=0, column=2, sticky='ew', padx=15)
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=3, sticky='ns')

        self.speed_label.grid(row=0, column=4, sticky='ew', padx=15)
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=5, sticky='ns')

        self.processed_label.grid(row=0, column=6, sticky='ew', padx=15)
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=7, sticky='ns')

        self.progress_bar.grid(row=0, column=8, sticky='ew', padx=15)
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=9, sticky='ns')

        self.duration_label.grid(row=0, column=10, sticky='ew', padx=15)
        sep9 = ttk.Separator(self, orient='vertical')
        sep9.grid(row=0, column=11, sticky='ns')

        self.preview_mode_label.grid(row=0, column=12, sticky='ew', padx=15)
        sep10 = ttk.Separator(self, orient='vertical')
        sep10.grid(row=0, column=13, sticky='ns')

        self.columnconfigure(8, weight=1)  # Make progress bar expand

    def on_resize(self, event):
        # Calculate an appropriate font size based on the current width
        new_font_size = max(8, min(15, int(self.winfo_width() / 130)))
        label_font = font.Font(family="Ubuntu Condensed", size=new_font_size)

        # Set the new font to all labels and progress bar
        for widget in [self.mode_label, self.item_id_label, self.speed_label, self.processed_label, self.duration_label,
                       self.preview_mode_label]:
            widget.config(font=label_font)

    def update_status(self):
        status_data: EventValidationStatusData = self.get_status_data()

        # Update labels
        self.mode_label.config(text=f"Mode: Event Validation")
        self.item_id_label.config(text=f"Item id: {status_data.item_id}")
        self.speed_label.config(text=f"Speed: {status_data.speed_per_hour} img/hour")

        position_percent = int((status_data.item_id + 1) / status_data.number_of_items * 100)
        self.processed_label.config(text=f"Position: {position_percent} % ({status_data.item_id + 1}/{status_data.number_of_items})")
        self.progress_bar["value"] = position_percent
        self.duration_label.config(text=f"Duration: {status_data.annotation_hours} hours")

        self.preview_mode_label.config(text=f"Preview mode: {status_data.view_mode}")

        # Schedule the next update
        self.after(10, self.update_status)


class EventValidationSideBar(tk.Frame):
    def __init__(self, parent, on_save_comment_callback: Callable, on_save_answer_callback: Callable, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent

        self.on_save_comment_callback = on_save_comment_callback
        self.on_save_answer_callback = on_save_answer_callback

        self.questions_map = json.loads(Value.get_value("fields"))

        self.answer_vars = OrderedDict()
        self.answer_buttons = OrderedDict()

        self.create_question_widgets()

        self.comment_label = tk.Label(self, text="Comment")
        self.comment_label.pack(anchor="w", padx=10, pady=2)
        self.comment_entry = tk.Text(self, wrap="word", height=2, width=40)
        self.comment_entry.pack(anchor="w", padx=10, pady=2)

        self.comment_entry.bind("<Escape>", self.save_comment)


    def update_display(self, answers, comment):
        self.update_question_widgets(answers)
        self.update_comment_display(comment)

    def update_comment_display(self, comment):
        self.comment_entry.delete("1.0", tk.END)
        self.comment_entry.insert("1.0", comment)

    def save_comment(self, event=None):
        new_comment = self.comment_entry.get("1.0", tk.END).strip()
        if self.on_save_comment_callback:
            self.on_save_comment_callback(new_comment)
        self.master.canvas_view.focus_set()

    def create_question_widgets(self, answers=None):
        for idx, question in enumerate(self.questions_map.keys()):
            frame = tk.Frame(self)
            frame.pack(anchor="w", padx=10, pady=2)
            question_text = f"[{idx + 1}] {question}"
            tk.Label(frame, text=question_text).pack(anchor='w', pady=2)
            initial_value = answers[question] if answers is not None else ""
            answer_var = tk.StringVar(value=initial_value)
            self.answer_vars[question] = answer_var

            self.answer_buttons[question] = []

            for option in self.questions_map[question].keys():  #  List of possible answers per question
                rb = tk.Radiobutton(
                    frame,
                    text=option,
                    variable=answer_var,
                    value=option,
                    command=lambda q=question, selected=option: self.save_answer(q, selected)
                )
                rb.pack(anchor='w', padx=5)
                self.answer_buttons[question].append(rb)
            self.apply_color(question, initial_value)

    def update_question_widgets(self, answers):
        for question in self.questions_map.keys():
            if question in self.answer_vars:
                self.answer_vars[question].set(answers[question])
            self.apply_color(question, answers.get(question))

    def save_answer(self, question, selected_answer):
        if self.on_save_answer_callback:
            self.on_save_answer_callback(question, selected_answer)
        self.apply_color(question, selected_answer)

    def apply_color(self, question, selected_answer):

        if question in self.answer_buttons:
            default_bg = tk.Radiobutton.cget(self, "bg")
            for rb in self.answer_buttons[question]:
                rb.config(bg=default_bg)

            if selected_answer in self.questions_map[question]:
                for rb in self.answer_buttons[question]:
                    if rb.cget("text") == selected_answer:
                        rb.config(bg=self.questions_map[question][selected_answer])


class VideoFrameSlider(tk.Frame):
    def __init__(self, parent, from_, to, on_change_callback: Callable = None, on_play_pause_callback: Callable = None,
                 on_stop_callback: Callable = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.on_change_callback = on_change_callback
        self.on_play_pause_callback = on_play_pause_callback
        self.on_stop_callback = on_stop_callback

        button_frame = tk.Frame(self)
        button_frame.pack(side="left", padx=10, pady=5, anchor="s")

        # Play/Pause Button
        self.play_button = tk.Button(button_frame, text="▶", width=3, font=("Arial", 10), command=self.toggle_play_pause)
        self.play_button.pack(side="left", padx=(0, 5), anchor="s")

        # Stop Button
        self.stop_button = tk.Button(button_frame, text="■", width=3, font=("Arial", 10), command=self.set_stop)
        self.stop_button.pack(side="left", padx=(5, 0), anchor="s")

        # Slider
        self.slider = tk.Scale(self, from_=from_, to=to, orient="horizontal", command=self.on_slider_change, length=500, sliderlength=30, width=20)
        self.slider.pack(side="right", fill="x", expand=True, padx=(10, 10), anchor="n")


    def on_slider_change(self, value):
        if self.on_change_callback is not None:
            self.on_change_callback(int(value))

    def toggle_play_pause(self):
        if self.on_play_pause_callback is not None:
            self.on_play_pause_callback()

    def set_stop(self):
        if self.on_stop_callback is not None:
            self.on_stop_callback()

    def update_play_pause_button(self, is_playing: bool):
        text = "II" if is_playing else "▶"
        self.play_button.config(text=text)

    def show(self):
        self.grid()

    def hide(self):
        self.grid_remove()


class BaseCanvasView(tk.Canvas):
    """
    Class Contains base functionality of displaying Images in window.
    """
    def __init__(self, parent: tk.Tk, root: tk.Tk, on_update_canvas_callback: Callable,
                 on_handle_key_callback: Callable, on_get_orig_image_callback: Callable,
                 on_update_time_counter_callback: Callable):
        super().__init__(parent, bg="black")

        self.on_update_canvas = on_update_canvas_callback
        self.on_handle_key = on_handle_key_callback
        self.on_get_orig_image = on_get_orig_image_callback
        self.on_update_time_counter = on_update_time_counter_callback

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

        self.on_update_canvas()

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

        self.on_handle_key(key=event.char.lower())

        self.last_key_press_time = time.time()
        self.on_update_time_counter("keyboard")

        self.update_frame = True
        self.last_key_event = None

    def fit_image(self):
        """Fits image inside the annotation_widget and re-calculates scale_factor"""
        win_w=self.winfo_width()
        win_h=self.winfo_height()

        orig_image = self.on_get_orig_image()
        img_h, img_w, c = orig_image.shape
        h_scale = win_h / img_h
        w_scale = win_w / img_w

        self.scale_factor = min(h_scale, w_scale)

        self.x0, self.y0 = 0, 0
        self.update_frame = True

    def update_canvas(self):
        self.process_last_key_press()
        if self.update_frame:

            # Convert the OpenCV image to a format suitable for Tkinter
            self.on_update_canvas()
            img = self.on_get_orig_image()
            if img is not None:
                cv_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
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
