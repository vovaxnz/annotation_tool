import time
from typing import Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from labeling import LabelingApp


class MainWindow(tk.Tk):
    def __init__(self, app: LabelingApp):
        super().__init__()
        self.title("Annotation Tool")
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

        self.update_frame = True

        self.bind("<Button-1>", self.scale_event_wrapper(self.handle_left_mouse_press))
        self.bind("<Button-3>", self.scale_event_wrapper(self.handle_right_mouse_press))

        self.bind("<B1-Motion>", self.scale_event_wrapper(self.handle_mouse_move))
        self.bind("<B3-Motion>", self.scale_event_wrapper(self.handle_mouse_move))

        self.bind("<Motion>", self.scale_event_wrapper(self.handle_mouse_hover))

        self.bind("<ButtonRelease-1>", self.scale_event_wrapper(self.handle_left_mouse_release))
        self.bind("<ButtonRelease-3>", self.scale_event_wrapper(self.handle_right_mouse_release))


        self.focus_set() # Set focus to the canvas to receive keyboard events 

        self.bind("<Key>", self.handle_key_press)  # Bind all key press events to handle_key_press

        self.bind("<MouseWheel>", self.on_mouse_wheel)  # For Windows
        self.bind("<Button-4>", self.on_mouse_wheel)  # For Unix/Linux, Zoom in
        self.bind("<Button-5>", self.on_mouse_wheel)  # For Unix/Linux, Zoom out

        # Drawing loop to update the canvas
        self.app.update_canvas()
        self.after(30, self.update_canvas)
        self.after(60, self.fit_image)

    def handle_left_mouse_press(self, event: tk.Event):
        self.app.handle_left_mouse_press(event.x, event.y)
        self.update_frame = True

    def handle_right_mouse_press(self, event: tk.Event):
        self.app.handle_right_mouse_press(event.x, event.y)
        self.update_frame = True

    def handle_mouse_move(self, event: tk.Event):
        self.app.handle_mouse_move(event.x, event.y)
        self.update_frame = True

    def handle_left_mouse_release(self, event: tk.Event):
        self.app.handle_left_mouse_release(event.x, event.y)
        self.update_frame = True

    def handle_right_mouse_release(self, event: tk.Event):
        self.app.handle_right_mouse_release(event.x, event.y)
        self.update_frame = True

    def handle_mouse_hover(self, event: tk.Event):
        # print("real position", event.x, event.y)
        self.app.handle_mouse_hover(event.x, event.y)
        self.update_frame = True

    def handle_key_press(self, event: tk.Event):
        if event.char.isdigit(): 
            number = int(event.char)
            self.app.change_label(number)
        elif event.char == "d":
            self.app.remove_selected_figure()
        elif event.char == "c":
            self.app.copy_figures_from_previous_image()
        elif event.char == "f":
            self.fit_image()
        elif event.char == "t":
            self.app.toggle_image_trash_tag()
        elif event.char == "h":
            self.app.switch_hiding_figures()
        elif event.char == "w":
            self.app.forward()
            self.fit_image()
        elif event.char == "q":
            self.app.backward()
            self.fit_image()
        elif event.char == "e":
            # TODO: Ask: are you sure you want to complete the project?
            self.app.complete_project()
            print("Annotation completed")
            # TODO: Exit application
        self.update_frame = True
        

    def fit_image(self):
        """Fits image inside the canvas and re-calculates scale_factor"""
        win_w=self.winfo_width()
        win_h=self.winfo_height()
        img_h, img_w, c = self.app.orig_image.shape
        h_scale = win_h / img_h 
        w_scale = win_w / img_w

        self.scale_factor = min(h_scale, w_scale)
        self.x0, self.y0 = 0, 0
        self.update_frame = True

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

        # Coordinates in pixels on the image
        cursor_x, cursor_y = self.xy_screen_to_image(event.x, event.y)

        # Determine zoom direction
        scale_multiplier = 1.1
        if event.num == 5 or event.delta == -120:  # Zoom out
            self.scale_factor = max(self.scale_factor / scale_multiplier, 0.5)
        elif event.num == 4 or event.delta == 120:  # Zoom in
            self.scale_factor = min(self.scale_factor * scale_multiplier, 8)


        self.x0 = (cursor_x - (event.x / self.scale_factor))
        self.y0 = (cursor_y - (event.y / self.scale_factor))

        # Restrict x0y0 to be no less than 0 and no more than 2/3 of image
        self.x0 = max(0, self.x0)
        self.y0 = max(0, self.y0)
        self.x0 = min(int(self.app.orig_image.shape[1]*0.6), self.x0)
        self.y0 = min(int(self.app.orig_image.shape[0]*0.6), self.y0)

        self.app.scale_factor = self.scale_factor

        self.app.cursor_x, self.app.cursor_y = self.xy_screen_to_image(event.x, event.y)

        self.app.update_canvas()
        self.update_frame = True


    def update_canvas(self):
        if self.update_frame:

            print("update", time.time())
            # Convert the OpenCV image to a format suitable for Tkinter
            cv_image = cv2.cvtColor(self.app.canvas, cv2.COLOR_BGR2RGB)
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

        self.after(30, self.update_canvas)
        

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
    
class ControlPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)