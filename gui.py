import time
from typing import Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from labeling import LabelingApp
from tkinter import ttk
from tkinter import font


class MainWindow(tk.Tk):
    def __init__(self, app: LabelingApp):
        super().__init__()
        self.title("Annotation Tool")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        # Create a container frame for better layout control
        self.container = tk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)

        # Use grid layout within the container
        self.container.grid_rowconfigure(0, weight=1)  # CanvasView row, make it expandable
        self.container.grid_columnconfigure(0, weight=1)  # Single column for simplicity

        # Initialize CanvasView and StatusBar within the container
        self.canvas_view = CanvasView(self.container, app)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")  # Make CanvasView expand in all directions

        self.status_bar = StatusBar(self.container, app)
        self.status_bar.grid(row=1, column=0, sticky='ew')  # StatusBar at the bottom, expanding horizontally

        # Ensure the StatusBar takes minimal vertical space
        self.container.grid_rowconfigure(1, weight=0, minsize=40)

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

        self.app.update_canvas()

        self.bind("<Configure>", self.on_resize)

    def handle_left_mouse_press(self, event: tk.Event):
        self.app.handle_left_mouse_press(event.x, event.y)
        self.update_frame = True
        self.app.update_time_counter()

    def handle_right_mouse_press(self, event: tk.Event):
        self.app.handle_right_mouse_press(event.x, event.y)
        self.update_frame = True
        self.app.update_time_counter()

    def handle_mouse_move(self, event: tk.Event):
        self.app.handle_mouse_move(event.x, event.y)
        self.update_frame = True

    def handle_left_mouse_release(self, event: tk.Event):
        self.app.handle_left_mouse_release(event.x, event.y)
        self.update_frame = True
        self.app.update_time_counter()

    def handle_right_mouse_release(self, event: tk.Event):
        self.app.handle_right_mouse_release(event.x, event.y)
        self.update_frame = True
        self.app.update_time_counter()

    def handle_mouse_hover(self, event: tk.Event):
        self.app.handle_mouse_hover(event.x, event.y)
        self.update_frame = True

    def on_resize(self, event):
        self.update_canvas()
        self.fit_image()

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
        self.app.update_time_counter()
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


class StatusBar(tk.Frame):
    def __init__(self, parent, app, **kw):
        super().__init__(parent, **kw)
        self.app: LabelingApp = app

        # Create labels within the status bar
        self.mode_label = tk.Label(self, bd=1)
        self.class_label = tk.Label(self, bd=1)
        self.trash_label = tk.Label(self, bd=1)
        self.hidden_label = tk.Label(self, bd=1)
        self.img_id_label = tk.Label(self, bd=1)
        self.speed_label = tk.Label(self, bd=1)
        self.processed_label = tk.Label(self, bd=1)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.duration_label = tk.Label(self, bd=1)

        # Place each label in the grid
        self.mode_label.grid(row=0, column=0, sticky='ew')
        sep1 = ttk.Separator(self, orient='vertical')
        sep1.grid(row=0, column=1, sticky='ns')
        
        self.class_label.grid(row=0, column=2, sticky='ew')
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=3, sticky='ns')
        
        self.trash_label.grid(row=0, column=4, sticky='ew')
        sep3 = ttk.Separator(self, orient='vertical')
        sep3.grid(row=0, column=5, sticky='ns')

        self.hidden_label.grid(row=0, column=6, sticky='ew')
        sep3 = ttk.Separator(self, orient='vertical')
        sep3.grid(row=0, column=7, sticky='ns')
        
        self.img_id_label.grid(row=0, column=8, sticky='ew')
        sep4 = ttk.Separator(self, orient='vertical')
        sep4.grid(row=0, column=9, sticky='ns')
        
        self.processed_label.grid(row=0, column=10, sticky='ew')
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=11, sticky='ns')
        
        self.progress_bar.grid(row=0, column=12, sticky='ew')
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=13, sticky='ns')
        
        self.speed_label.grid(row=0, column=14, sticky='ew')
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=15, sticky='ns')
        
        self.duration_label.grid(row=0, column=16, sticky='ew')
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=17, sticky='ns')

        # Ensure the progress bar expands to fill available space 
        self.columnconfigure(12, weight=1)

        # Apply font settings to labels
        label_font = font.Font(family="Ubuntu Condensed", size=15)
        self.mode_label.config(font=label_font)
        self.class_label.config(font=label_font)
        self.trash_label.config(font=label_font)
        self.hidden_label.config(font=label_font)
        self.img_id_label.config(font=label_font)
        self.speed_label.config(font=label_font)
        self.processed_label.config(font=label_font)
        self.duration_label.config(font=label_font)

        # Set padding around labels to prevent overflow
        for col in range(0, 17):
            self.grid_columnconfigure(col, pad=30)

        # Sef fixed size
        self.grid_columnconfigure(2, minsize=150)  # For class_label
        self.grid_columnconfigure(4, minsize=120)  # For trash_label
        self.grid_columnconfigure(6, minsize=120)  # For hidden_label
        self.grid_columnconfigure(8, minsize=120)  # For img_id_label

        self.update_status()

    def update_status(self):
        status_data = self.app.status_data 
        
        # Update labels
        self.mode_label.config(text=f"Mode: {status_data.annotation_mode}")
        self.class_label.config(text=f"Class: {status_data.selected_class}", bg=status_data.class_color)
        trash_text = "Trash" if status_data.is_trash else "not Trash"
        trash_color = "red" if status_data.is_trash else self.trash_label.master.cget('bg')
        self.trash_label.config(text=trash_text, bg=trash_color)

        hidden_text = "All Hidden" if status_data.figures_hidden else "All Visible"
        hidden_color = "blue" if status_data.figures_hidden else self.hidden_label.master.cget('bg')
        self.hidden_label.config(text=hidden_text, bg=hidden_color)

        self.img_id_label.config(text=f"Img id: {status_data.img_id}")
        self.speed_label.config(text=f"Speed: {status_data.speed_per_hour} img/hour")
        self.processed_label.config(text=f"Processed: {status_data.processed_percent} % ({status_data.number_of_processed}/{status_data.number_of_images})")
        self.progress_bar["value"] = status_data.processed_percent
        self.duration_label.config(text=f"Duration: {status_data.annotation_hours} hours")
        
        # Schedule the next update
        self.after(30, self.update_status)