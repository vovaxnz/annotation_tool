import os
import sys
import time
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from api_requests import ProjectData, get_projects_data
from get_labeling_app import complete_annotation, download_project, get_labeling_app
from gui_utils import ImageIdForm, SettingsManager, get_loading_window
from import_annotations import overwrite_annotations
from labeling.annotation import LabelingApp
from tkinter import ttk
from tkinter import font
from tkinter import messagebox
from jinja2 import Environment, FileSystemLoader
import tkinterweb
from models import Label
from config import templates_path


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Annotation tool")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        # Create a container frame for better layout control
        self.container = tk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)

        # Use grid layout within the container
        self.container.grid_rowconfigure(0, weight=1)  # CanvasView row, make it expandable
        self.container.grid_columnconfigure(0, weight=1)  # Single column for simplicity
        self.container.grid_rowconfigure(1, weight=0, minsize=40) # container for StatusBar

        self.canvas_view = None
        self.status_bar = None
        
        # Create a menu bar
        self.menu_bar = tk.Menu(self)

        # Create a menu and add it to the menu bar
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)

        self.menu_bar.add_cascade(label="Project", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.update_menu(initial=True)
        
        # Check if running on macOS
        if sys.platform == "darwin":
            # For macOS, setting the menu on the root should automatically handle it,
            # but if it doesn't appear in the top bar, we force it here
            self.tk.call('tk::mac::standardAboutPanel')

        # Attach the menu bar to the window
        self.config(menu=self.menu_bar)
        
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

    def update_menu(self, initial=False):
        # Clear existing menu items
        self.file_menu.delete(0, 'end')
        self.help_menu.delete(0, 'end')

        # Add basic menu items
        self.file_menu.add_command(label="Open", command=self.open_project)
        self.file_menu.add_command(label="Download", command=self.download_project)
        self.file_menu.add_command(label="Settings", command=self.open_settings)
        self.help_menu.add_command(label="How to use this tool?", command=self.show_how)
        self.help_menu.add_command(label="Hotkeys", command=self.show_hotkeys)
        
        # Add dynamic items only after initial setup
        if not initial:
            self.file_menu.add_command(label="Go to image", command=self.go_to_image_id) 
            self.file_menu.add_command(label="Complete the project", command=self.complete_project)
            self.file_menu.add_command(label="Download and overwrite annotations", command=self.canvas_view.overwrite_annotations)
            self.help_menu.add_command(label="Classes", command=self.show_classes)
            self.help_menu.add_command(label="Review Labels", command=self.show_review_labels)

    def set_canvas(self, labeling_app: LabelingApp): 
        self.canvas_view = CanvasView(self.container, root=self, app=labeling_app)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")  # Make CanvasView expand in all directions
        self.canvas_view.set_close_callback(self.destroy)

        self.status_bar = StatusBar(self.container, labeling_app)
        self.status_bar.grid(row=1, column=0, sticky='ew')  # StatusBar at the bottom, expanding horizontally

    def remove_canvas(self):
        if self.canvas_view is not None:
            self.canvas_view.app.save_image()
            self.canvas_view.app.save_state()
            self.canvas_view.destroy()
            self.canvas_view = None

        if self.status_bar is not None:
            self.status_bar.destroy()
            self.status_bar = None 

    def open_project(self):
        loading_window = get_loading_window(text="Getting your active projects...", root=self)
        projects_data = get_projects_data()
        loading_window.destroy()
        ps = ProjectSelector(projects_data, root=self)
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            if self.canvas_view is not None:
                self.remove_canvas()
            labeling_app = get_labeling_app(project_data, root=self)
            self.set_canvas(labeling_app)
            self.title(f"Labeling Project {project_data.id}")
            self.update_menu()

    def download_project(self):
        loading_window = get_loading_window(text="Getting your active projects...", root=self)
        projects_data = get_projects_data()
        loading_window.destroy()
        ps = ProjectSelector(projects_data, root=self)
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            download_project(project_data=project_data, root=self)

    def complete_project(self):
        agree = messagebox.askokcancel("Project Completion", "Are you sure you want to complete the project?")
        if agree:
            self.canvas_view.app.save_image()
            self.canvas_view.app.save_state()
            self.canvas_view.app.ready_for_export = True
            complete_annotation(self.canvas_view.app, root=self)
        self.remove_canvas()
        self.update_menu(initial=True)
        self.title(f"Annotation tool")

    def open_settings(self):
        SettingsManager(root=self)
        
    def go_to_image_id(self):
        form = ImageIdForm(root=self, max_id=len(self.canvas_view.app.img_names))
        img_id = form.get_image_id()
        self.canvas_view.app.go_to_image_by_id(img_id - 1)
        self.canvas_view.update_frame = True

    def on_window_close(self):
        if self.canvas_view is not None:
            self.canvas_view.app.save_image()
            self.canvas_view.app.save_state()
        self.destroy()

    def _show_html_window(self, title, html_content):
        window = tk.Toplevel(self)
        window.title(title)

        html_frame = tkinterweb.HtmlFrame(window, messages_enabled=False)
        html_frame.load_html(html_content)
        html_frame.pack(fill="both", expand=True)

        window.update_idletasks()
        window.update()

    def show_hotkeys(self):
        template_path = os.path.join(templates_path, "hotkeys.html")
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        self._show_html_window(title="Hotkeys", html_content=html_content)

    def show_how(self):
        template_path = os.path.join(templates_path, "how.html")
        with open(template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        self._show_html_window(title="How to use this tool?", html_content=html_content)

    def show_classes(self):
        data = [
            {
                "name": l.name,
                "color": l.color,
                "hotkey": l.hotkey,
            } for l in Label.get_figure_labels()
        ]
        
        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        self._show_html_window(title="Classes", html_content=html_content)

    def show_review_labels(self):
        data = [
            {
                "name": l.name,
                "color": l.color,
                "hotkey": l.hotkey,
            } for l in Label.get_review_labels()
        ]
        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template('classes.html')
        html_content = template.render(data=data)
        self._show_html_window(title="Classes", html_content=html_content)


class CanvasView(tk.Canvas):
    def __init__(self, parent, root: tk.Tk, app: LabelingApp):
        super().__init__(parent, bg="black")

        self.app = app

        self.parent=root

        self.scale_factor = 1.0
        self.x0, self.y0 = 0, 0

        # For calculating panning delta
        self.click_win_x, self.click_win_y = 0, 0
        self.start_x0, self.start_y0 = 0, 0
        self.panning = False

        self.update_frame = True

        self.last_key_press_time = None

        self.bind("<Button-1>", self.scale_event_wrapper(self.handle_left_mouse_press))
        self.bind("<Button-3>", self.handle_right_mouse_press)

        self.bind("<B1-Motion>", self.scale_event_wrapper(self.handle_mouse_move))
        self.bind("<B3-Motion>", self.handle_right_mouse_motion)

        self.bind("<Motion>", self.scale_event_wrapper(self.handle_mouse_hover))

        self.bind("<ButtonRelease-1>", self.scale_event_wrapper(self.handle_left_mouse_release))
        self.bind("<ButtonRelease-3>", self.scale_event_wrapper(self.handle_right_mouse_release))

        self.focus_set() # Set focus to the canvas to receive keyboard events 

        self.bind("<Key>", self.handle_key_press)
        # self.bind("<KeyRelease>", self.handle_key_release) 

        self.bind("<MouseWheel>", self.on_mouse_wheel)  # For Windows
        self.bind("<Button-4>", self.on_mouse_wheel)  # For Unix/Linux, Zoom in
        self.bind("<Button-5>", self.on_mouse_wheel)  # For Unix/Linux, Zoom out

        self.app.update_canvas()

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
        self.bind("<KeyRelease-a>", self.handle_key_a_release)

        self.close_callback = None

    def on_shift_press(self, event):
        self.app.on_shift_press()
        self.update_frame = True

    def set_close_callback(self, callback):
        self.close_callback = callback

    def close(self):
        self.destroy()
        if self.close_callback:
            self.close_callback()

    def handle_right_mouse_motion(self, event: tk.Event):
        if self.panning:
            win_cursor_x, win_cursor_y = event.x, event.y
            
            delta_x = (self.click_win_x - win_cursor_x) / self.scale_factor
            self.x0 = self.start_x0 + delta_x
            delta_y = (self.click_win_y - win_cursor_y) / self.scale_factor
            self.y0 = self.start_y0 + delta_y 
            

            self.x0 = max(0, self.x0)
            self.y0 = max(0, self.y0)
            self.x0 = min(int(self.app.orig_image.shape[1]*0.9), self.x0)
            self.y0 = min(int(self.app.orig_image.shape[0]*0.9), self.y0)

        self.scale_event_wrapper(self.handle_mouse_move)(event)


    def handle_right_mouse_press(self, event: tk.Event):

        self.update_frame = True
        self.app.update_time_counter()

        self.panning = True
        self.click_win_x, self.click_win_y = event.x, event.y
        self.start_x0, self.start_y0 = self.x0, self.y0

    def handle_left_mouse_press(self, event: tk.Event):
        self.app.handle_left_mouse_press(event.x, event.y)
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
        self.update_frame = True
        self.app.update_time_counter()
        self.panning = False

    def handle_mouse_hover(self, event: tk.Event):
        self.app.handle_mouse_hover(event.x, event.y)
        self.update_frame = True

    def handle_space(self, event: tk.Event):
        self.app.handle_space()
        self.update_frame = True

    def handle_esc(self, event: tk.Event):
        self.app.handle_esc()
        self.update_frame = True

    def on_resize(self, event):
        self.update_canvas()
        self.fit_image()

    def handle_key_a_press(self, event: tk.Event):
        self.last_a_press_time = time.time()
        if not self.a_held_down:

            self.app.start_selecting_class()
            self.update_frame = True
            self.app.update_time_counter()

            self.a_held_down = True
            
    def handle_key_a_release(self, event: tk.Event):
        self.after(100, self.check_key_a_pressed)

    def check_key_a_pressed(self):
        if time.time() - self.last_a_press_time > 0.1:
            self.app.end_selecting_class()
            self.update_frame = True
            self.a_held_down = False


    def handle_key_press(self, event: tk.Event):
        
        ctrl_pressed = (event.state & 0x0004) != 0  # Control key mask
        cmd_pressed = (event.state & 0x0100) != 0  # Command key (macOS) mask

        if ctrl_pressed or cmd_pressed:  # Check if Ctrl or Command key is down
            if event.keysym.lower() == 'z':
                self.app.undo()
            elif event.keysym.lower() == 'y':
                self.app.redo()
            elif event.keysym.lower() == 'c':
                self.app.copy()
            elif event.keysym.lower() == 'v':
                self.app.paste()

            self.update_frame = True
            self.app.update_time_counter()
            return
    
        current_time = time.time()
        if self.last_key_press_time is None or (current_time - self.last_key_press_time) >= self.keyboard_events_interval:
            self.last_key_press_time = current_time # Prevent too frequent key press
        else:
            return

        if event.char.isdigit(): 
            self.app.change_label(event.char)
        elif event.char.lower() == "d":
            self.app.delete_command()
        elif event.char.lower() == "f":
            self.fit_image()
        elif event.char.lower() == "t":
            self.app.toggle_image_trash_tag()
        elif event.char.lower() == "e":
            self.app.switch_hiding_figures()
        elif event.char.lower() == "r":
            self.app.switch_hiding_review_labels() 
        elif event.char.lower() == "n":
            self.app.switch_object_names_visibility() 
        elif event.char.lower() == "w":
            self.app.forward()
            self.fit_image()
            self.scale_event_wrapper(self.handle_mouse_hover)(event)
        elif event.char.lower() == "q":
            self.app.backward()
            self.fit_image()
            self.scale_event_wrapper(self.handle_mouse_hover)(event)
        self.app.update_time_counter()
        self.update_frame = True
        

    def overwrite_annotations(self):
        agree = messagebox.askokcancel("Overwrite", "Are you sure you want to download annotations and overwrite your annotations with them? All your work will be overwritten")
        if agree:
            root = get_loading_window(text="Downloading and overwriting annotations...", root=self.parent)
            overwrite_annotations(self.app.project_id)
            self.app.load_image()
            root.destroy()
            self.update_frame = True
            self.update_canvas()
            messagebox.showinfo("Success", "The annotations have been overwritten")


    def fit_image(self):
        """Fits image inside the canvas and re-calculates scale_factor"""
        win_w=self.winfo_width()
        win_h=self.winfo_height()
        img_h, img_w, c = self.app.orig_image.shape
        h_scale = win_h / img_h 
        w_scale = win_w / img_w

        self.scale_factor = min(h_scale, w_scale)

        self.app.scale_factor = self.scale_factor
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
            self.scale_factor = min(self.scale_factor * scale_multiplier, 10)


        self.x0 = (cursor_x - (event.x / self.scale_factor))
        self.y0 = (cursor_y - (event.y / self.scale_factor))

        # Restrict x0y0 to be no less than 0 and no more than 2/3 of image
        self.x0 = max(0, self.x0)
        self.y0 = max(0, self.y0)
        self.x0 = min(int(self.app.orig_image.shape[1]*0.9), self.x0)
        self.y0 = min(int(self.app.orig_image.shape[0]*0.9), self.y0)

        self.app.scale_factor = self.scale_factor

        self.app.cursor_x, self.app.cursor_y = self.xy_screen_to_image(event.x, event.y)

        self.update_frame = True

    def update_canvas(self):
        if self.update_frame:

            # Convert the OpenCV image to a format suitable for Tkinter
            self.app.update_canvas()
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

