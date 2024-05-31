import os
import sys
import time
from typing import Callable, List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from api_requests import get_projects_data
from enums import AnnotationMode
from get_labeling_app import complete_annotation, download_project, get_labeling_app
from gui_utils import AnnotationStatusBar, FilteringStatusBar, ImageIdForm, ProjectSelector, SettingsManager, get_loading_window
from import_annotations import overwrite_annotations
from labeling.abstract_labeling_app import AbstractLabelingApp, ProjectData
from tkinter import ttk
from tkinter import font
from tkinter import messagebox
from jinja2 import Environment, FileSystemLoader
import tkinterweb
from models import Label
from config import templates_path
from config import settings

from pynput.keyboard import Listener

from path_manager import get_local_projects_data
from utils import check_url_rechable
from tkinter import PhotoImage

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        icon = PhotoImage(file=os.path.join(os.path.dirname(os.path.realpath(__file__)), "icon.png"))
        self.iconphoto(True, icon)
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
            if self.canvas_view.app.annotation_mode is AnnotationMode.FILTERING:
                return
            self.file_menu.add_command(label="Download and overwrite annotations", command=self.canvas_view.overwrite_annotations)
            self.help_menu.add_command(label="Classes", command=self.show_classes)
            self.help_menu.add_command(label="Review Labels", command=self.show_review_labels)

    def set_canvas(self, labeling_app: AbstractLabelingApp): 
        self.canvas_view = CanvasView(self.container, root=self, app=labeling_app)
        self.canvas_view.grid(row=0, column=0, sticky="nsew")  # Make CanvasView expand in all directions
        self.canvas_view.set_close_callback(self.destroy)

        if labeling_app.annotation_mode is AnnotationMode.FILTERING:
            self.status_bar = FilteringStatusBar(self.container, labeling_app)
        else:
            self.status_bar = AnnotationStatusBar(self.container, labeling_app)

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
        
        try:
            projects_data = get_projects_data()
        except:
            messagebox.showinfo("Error", "Unable to reach a web service. You`ll be shown only already downloaded projects.")
            projects_data = get_local_projects_data()
    
        loading_window.destroy()
        ps = ProjectSelector(projects_data, root=self)
        project_data: ProjectData = ps.select()
        if project_data is not None: 
            if self.canvas_view is not None:
                self.remove_canvas()
            labeling_app = get_labeling_app(project_data, root=self)
            self.set_canvas(labeling_app)
            self.title(f"Project {project_data.id}")
            self.update_menu()

    def download_project(self):
        loading_window = get_loading_window(text="Getting your active projects...", root=self)

        try:
            projects_data = get_projects_data()
        except:
            messagebox.showinfo("Error", "Unable to reach a web service. You can not download a project now.")
            return
        
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
            if check_url_rechable(settings.api_url):
                complete_annotation(self.canvas_view.app, root=self)
            else:
                messagebox.showinfo("Error", "Unable to reach a web service. Project is not completed. You can complete it later after resume access to the web service.")
        self.remove_canvas()
        self.update_menu(initial=True)
        self.title(f"Annotation tool")

    def set_update_canvas(self):
        if self.canvas_view is not None:
            self.canvas_view.update_frame=True

    def open_settings(self):
        SettingsManager(root=self, at_exit=lambda : self.set_update_canvas())
        
    def go_to_image_id(self):
        form = ImageIdForm(root=self, max_id=self.canvas_view.app.img_number)
        img_id = form.get_image_id()
        if img_id is not None:
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
    def __init__(self, parent, root: tk.Tk, app: AbstractLabelingApp):
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

        self.fit_at_img_change = True

        self.last_key_press_time = None

        self.bind("<Button-1>", self.scale_event_wrapper(self.handle_left_mouse_press))
        self.bind("<Button-3>", self.handle_right_mouse_press)

        self.bind("<B1-Motion>", self.scale_event_wrapper(self.handle_mouse_move))
        self.bind("<B3-Motion>", self.handle_right_mouse_motion)

        self.bind("<Motion>", self.scale_event_wrapper(self.handle_mouse_hover))

        self.bind("<ButtonRelease-1>", self.scale_event_wrapper(self.handle_left_mouse_release))
        self.bind("<ButtonRelease-3>", self.scale_event_wrapper(self.handle_right_mouse_release))

        self.focus_set() # Set focus to the canvas to receive keyboard events 

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
        self.bind("<KeyRelease-a>", self.handle_key_a_release)

        self.close_callback = None

        self.last_key_event = None
        self.any_key_pressed = False
        self.current_pressed_key = None

        # Start listening to the keyboard
        self.listener = Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.listener.start()

        self.app.update_canvas()

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


    # TODO: Move handle_key_a_press, handle_key_a_release, check_key_a_pressed to AnnotationApp
    def handle_key_a_press(self, event: tk.Event):
        self.last_a_press_time = time.time()
        if not self.a_held_down:

            self.app.start_selecting_class()
            self.update_frame = True
            self.app.update_time_counter()

            self.a_held_down = True
            
    def handle_key_a_release(self, event: tk.Event):
        self.after(int(self.keyboard_events_interval * 1000), self.check_key_a_pressed)

    def check_key_a_pressed(self):
        if time.time() - self.last_a_press_time > self.keyboard_events_interval:
            self.app.end_selecting_class()
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
                self.app.undo()
            elif event.keysym.lower() == 'y':
                self.app.redo()
            elif event.keysym.lower() == 'c':
                self.app.copy()
            elif event.keysym.lower() == 'v':
                self.app.paste()
            time.sleep(0.1) # Added to prevent too fast redo or paste

            self.update_frame = True
            self.app.update_time_counter()
            return
        if event.char.lower() == "w" or event.char.lower() == "p":
            self.app.forward()
            if self.fit_at_img_change:
                self.fit_image()
            self.scale_event_wrapper(self.handle_mouse_hover)(event)
            self.update_frame = True
        elif event.char.lower() == "q" or event.char.lower() == "o":
            self.app.backward()
            if self.fit_at_img_change:
                self.fit_image()
            self.scale_event_wrapper(self.handle_mouse_hover)(event)
            self.update_frame = True
        elif event.char.lower() == "f":
            self.fit_image()
        else:
            self.app.handle_key(key=event.char.lower())

        self.app.update_time_counter()

        self.update_frame = True
        self.last_key_event = None
        

    def overwrite_annotations(self):

        if not check_url_rechable(settings.api_url):
            messagebox.showinfo("Error", "Unable to reach a web service")
            return
        
        agree = messagebox.askokcancel("Overwrite", "Are you sure you want to download annotations and overwrite your annotations with them? All your work will be overwritten")
        if agree:
            root = get_loading_window(text="Downloading and overwriting annotations...", root=self.parent)
            overwrite_annotations(project_id=self.app.project_id, project_uid=self.app.project_uid)
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
        self.process_last_key_press()
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

