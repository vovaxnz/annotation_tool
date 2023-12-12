from typing import Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from labeling import LabelingApp


class MainWindow(tk.Tk):
    def __init__(self, app: LabelingApp):
        super().__init__()
        self.title("Rectangle Drawing Tool")
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Set window size to screen size
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.canvas_view = CanvasView(self, app)
        self.control_panel = ControlPanel(self)
        self.canvas_view.pack(side="left", fill="both", expand=True)
        self.control_panel.pack(side="right", fill="y")

class CanvasView(tk.Canvas):
    def __init__(self, parent, app: LabelingApp):
        super().__init__(parent, bg="black") 

        self.app = app

        self.scale_factor = 1.0
        self.x0, self.y0 = 0, 0

        self.bind("<Button-1>", self.scale_event_wrapper(self.handle_left_click))
        self.bind("<Button-2>", self.scale_event_wrapper(self.handle_middle_click))
        self.bind("<Button-3>", self.scale_event_wrapper(self.handle_right_click))
        self.bind("<B1-Motion>", self.scale_event_wrapper(self.handle_mouse_move))
        self.bind("<B3-Motion>", self.scale_event_wrapper(self.handle_mouse_move))
        self.bind("<ButtonRelease-1>", self.scale_event_wrapper(self.handle_mouse_release))
        self.bind("<ButtonRelease-3>", self.scale_event_wrapper(self.handle_mouse_release))

        # Set focus to the canvas to receive keyboard events
        self.focus_set()
        self.bind("<e>", self.handle_e_press)
        self.bind("<q>", self.handle_q_press)
        self.bind("<w>", self.handle_w_press)
        self.bind("<a>", self.handle_a_press)
        self.bind("<s>", self.handle_s_press)

        self.bind("<MouseWheel>", self.on_mouse_wheel)  # For Windows
        self.bind("<Button-4>", self.on_mouse_wheel)  # For Unix/Linux, Zoom in
        self.bind("<Button-5>", self.on_mouse_wheel)  # For Unix/Linux, Zoom out

        # Drawing loop to update the canvas
        self.after(30, self.update_canvas)

    def handle_left_click(self, event: tk.Event):
        self.app.handle_left_click(event.x, event.y)

    def handle_right_click(self, event: tk.Event):
        self.app.handle_right_click(event.x, event.y)

    def handle_middle_click(self, event: tk.Event):
        self.app.handle_middle_click(event.x, event.y)

    def handle_mouse_move(self, event: tk.Event):
        self.app.handle_mouse_move(event.x, event.y)

    def handle_mouse_release(self, event: tk.Event):
        self.app.handle_mouse_release(event.x, event.y)

    def handle_e_press(self, event: tk.Event):
        self.app.export_data()

    def handle_q_press(self, event: tk.Event):
        self.app.backward()
        self.fit_scale_for_image()

    def handle_w_press(self, event: tk.Event):
        self.app.forward()
        self.fit_scale_for_image()

    def handle_a_press(self, event: tk.Event):
        self.app.switch_drawing_figures()

    def handle_s_press(self, event: tk.Event):
        self.fit_scale_for_image()

    def fit_scale_for_image(self):
        win_w=self.winfo_width()
        win_h=self.winfo_height()
        img_h, img_w, c = self.app.canvas.image.shape
        print('img_h, img_w, c', img_h, img_w, c)
        print('win_w, win_h', win_w, win_h)
        h_scale = win_h / img_h 
        w_scale = win_w / img_w

        self.scale_factor = min(h_scale, w_scale)
        self.x0, self.y0 = 0, 0

    def scale_event_wrapper(self, handler):
        # Wrapper function to adjust event coordinates
        def wrapped_event(event):
            # Adjust the event coordinates based on the current scale
            scaled_event = event 
            scaled_event.x, scaled_event.y = self.xy_screen_to_image(event.x, event.y)
            # Call the actual event handler with the scaled event
            return handler(scaled_event)

        return wrapped_event

    def on_mouse_wheel(self, event):

        cursor_x, cursor_y = self.xy_screen_to_image(event.x, event.y)

        cursor_old_x = cursor_x * self.scale_factor
        cursor_old_y = cursor_y * self.scale_factor

        scale_multiplier = 1.1  # Define how much each scroll affects the scale
        if event.num == 5 or event.delta == -120:  # Scroll down or backward
            self.scale_factor /= scale_multiplier
            if self.scale_factor < 0.1:  # Prevent too much zoom out
                self.scale_factor = 0.1
        if event.num == 4 or event.delta == 120:  # Scroll up or forward
            self.scale_factor *= scale_multiplier
            if self.scale_factor > 8:  # Prevent too much zoom in
                self.scale_factor = 8

        cursor_new_x = cursor_x * self.scale_factor
        cursor_new_y = cursor_y * self.scale_factor

        x_scale_delta = cursor_new_x - cursor_old_x
        y_scale_delta = cursor_new_y - cursor_old_y
        
        self.x0 += x_scale_delta
        self.y0 += y_scale_delta

        self.x0 = max(0, self.x0)
        self.y0 = max(0, self.y0)

    def update_canvas(self):
        # Convert the OpenCV image to a format suitable for Tkinter
        cv_image = cv2.cvtColor(self.app.canvas.canvas, cv2.COLOR_BGR2RGB)
        cv_image = self.scale_image(img=cv_image, x0=self.x0, y0=self.y0, scale=self.scale_factor)
        pil_image = Image.fromarray(cv_image)
        tk_image = ImageTk.PhotoImage(image=pil_image)

        # Clear the current contents of the canvas
        self.delete("all")

        # Add new image to the canvas
        self.create_image(0, 0, anchor="nw", image=tk_image)

        # Keep a reference to the image to prevent garbage collection
        self.tk_image = tk_image

        self.after(30, self.update_canvas)

    def xy_screen_to_image(self, x, y) -> Tuple[int, int]:
        x_orig = (x + self.x0) / self.scale_factor
        y_orig = (y + self.y0) / self.scale_factor
        return x_orig, y_orig

    def scale_image(self, img: np.ndarray, x0: int, y0: int, scale: float) -> np.ndarray:

        # Get the original dimensions of the image
        h, w = img.shape[:2]

        # Compute the new dimensions
        new_width = int(w * scale)
        new_height = int(h * scale)

        # Resize the image
        resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        x0 = max(x0, 0)
        y0 = max(y0, 0)

        # Crop or pad the image
        cropped = resized[int(y0):int(y0+h), int(x0):int(x0+w)]

        return cropped
    

class ControlPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)