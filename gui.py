import os
import time
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from api_requests import ProjectData, get_projects_data
from get_labeling_app import complete_annotation, get_labeling_app
from gui_utils import SettingsManager, get_loading_window
from import_annotations import overwrite_annotations
from labeling import LabelingApp
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
        
        # Attach the menu bar to the window
        self.config(menu=self.menu_bar)
        
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

    def update_menu(self, initial=False):
        # Clear existing menu items
        self.file_menu.delete(0, 'end')
        self.help_menu.delete(0, 'end')

        # Add basic menu items
        self.file_menu.add_command(label="Open", command=self.open_project)
        self.file_menu.add_command(label="Settings", command=self.open_settings)
        self.help_menu.add_command(label="How to use this tool?", command=self.show_how)
        self.help_menu.add_command(label="Hotkeys", command=self.show_hotkeys)
        self.help_menu.add_command(label="Review Labels", command=self.show_review_labels)
        
        # Add dynamic items only after initial setup
        if not initial:
            self.file_menu.add_command(label="Go to the first image", command=self.canvas_view.go_to_first_image)
            self.file_menu.add_command(label="Complete the project", command=self.complete_project)
            self.file_menu.add_command(label="Download and overwrite annotations", command=self.canvas_view.overwrite_annotations)
            self.help_menu.add_command(label="Classes", command=self.show_classes)

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

    def complete_project(self):
        agree = messagebox.askokcancel("Project Completion", "Are you sure you want to complete the project?")
        if agree:
            self.canvas_view.app.save_image()
            self.canvas_view.app.save_state()
            self.canvas_view.app.ready_for_export = True
            complete_annotation(self.canvas_view.app, root=self)
        self.remove_canvas()
        self.title(f"Annotation tool")

    def open_settings(self):
        SettingsManager(root=self)
        

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

        self.bind("<Key>", self.handle_key_press)  # Bind all key press events to handle_key_press

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

    def handle_key_press(self, event: tk.Event):

        current_time = time.time()
        if self.last_key_press_time is None or (current_time - self.last_key_press_time) >= 0.2:
            self.last_key_press_time = current_time # Prevent too frequent key press
        else:
            return
        
        if event.char.isdigit(): 
            self.app.change_label(event.char)
        elif event.char.lower() == "d":
            self.app.delete_command()
        elif event.char.lower() == "c":
            self.app.copy_figures_from_previous_image()
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
        
    def go_to_first_image(self):
        self.app.go_to_first_image()
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
        
        self.class_label.grid(row=0, column=2, sticky='ew', padx=15)
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=3, sticky='ns')
        
        self.trash_label.grid(row=0, column=4, sticky='ew', padx=15)
        sep3 = ttk.Separator(self, orient='vertical')
        sep3.grid(row=0, column=5, sticky='ns')
        
        self.hidden_label.grid(row=0, column=6, sticky='ew', padx=15)
        sep4 = ttk.Separator(self, orient='vertical')
        sep4.grid(row=0, column=7, sticky='ns')
        
        self.img_id_label.grid(row=0, column=8, sticky='ew', padx=15)
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=9, sticky='ns')
        
        self.speed_label.grid(row=0, column=10, sticky='ew', padx=15)
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=11, sticky='ns')
        
        self.processed_label.grid(row=0, column=12, sticky='ew', padx=15)
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=13, sticky='ns')
        
        self.progress_bar.grid(row=0, column=14, sticky='ew', padx=15)
        self.columnconfigure(14, weight=1)  # Make progress bar expand
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=15, sticky='ns')

        self.duration_label.grid(row=0, column=16, sticky='ew', padx=15)
        sep9 = ttk.Separator(self, orient='vertical')
        sep9.grid(row=0, column=17, sticky='ns')

    def on_resize(self, event):
        # Calculate an appropriate font size based on the current width
        new_font_size = max(8, min(15, int(self.winfo_width() / 130))) 
        label_font = font.Font(family="Ubuntu Condensed", size=new_font_size)
        
        # Set the new font to all labels and progress bar
        for widget in [self.mode_label, self.class_label, self.trash_label, self.hidden_label,
                       self.img_id_label, self.speed_label, self.processed_label, self.duration_label]:
            widget.config(font=label_font)

    def update_status(self):
        status_data = self.app.status_data 
        
        # Update labels
        self.mode_label.config(text=f"Mode: {status_data.annotation_mode}: {status_data.annotation_stage}")
        self.class_label.config(text=f"Class: {status_data.selected_class}", bg=status_data.class_color)
        trash_text = "Trash" if status_data.is_trash else "not Trash"
        trash_color = "red" if status_data.is_trash else self.trash_label.master.cget('bg')
        self.trash_label.config(text=trash_text, bg=trash_color)

        hidden_text = "All Visible"
        hidden_text = "Review Hidden" if status_data.review_labels_hidden else hidden_text
        hidden_text = "All Hidden" if status_data.figures_hidden  else hidden_text
        
        hidden_color = self.hidden_label.master.cget('bg') if hidden_text == "All Visible" else "blue"
        self.hidden_label.config(text=hidden_text, bg=hidden_color)

        self.img_id_label.config(text=f"Img id: {status_data.img_id}")
        self.speed_label.config(text=f"Speed: {status_data.speed_per_hour} img/hour")

        position_percent = int((status_data.img_id + 1) / status_data.number_of_images * 100)
        self.processed_label.config(text=f"Position: {position_percent} % ({status_data.img_id + 1}/{status_data.number_of_images})")
        self.progress_bar["value"] = position_percent
        self.duration_label.config(text=f"Duration: {status_data.annotation_hours} hours")
        
        # Schedule the next update
        self.after(30, self.update_status)


class ProjectSelector:
    def __init__(self, projects: List[ProjectData], root: tk.Tk):
        self.projects = projects
        self.selected_project = None
        self.parent = root

    def select(self):
        self.root = tk.Toplevel(self.parent)
        self.root.title("Select Project")

        # Set window size
        window_width = 300
        window_height = 500

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate x and y coordinates for the Tk root window
        x = (screen_width / 2) - (window_width / 2)
        y = (screen_height / 2) - (window_height / 2)

        # Set the dimensions of the window and where it is placed
        self.root.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))

        self.text = tk.Label(self.root, text="Select project")
        self.text.pack(pady=10)

        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(self.root, width=280, height=450)  # Adjusted size to fit within the window
        self.scrollbar = tk.Scrollbar(self.root, orient='vertical', command=self.canvas.yview)
        self.canvas.config(yscrollcommand=self.scrollbar.set)

        self.scroll_frame = tk.Frame(self.canvas)
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        if not self.projects:
            self._display_no_projects_message()
        else:
            self._create_project_buttons()

        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

        self.root.wait_window(self.root)

        return self.selected_project

    def _create_project_buttons(self):
        for project in self.projects:
            text = f"{project.id} ({project.mode.name}: {project.stage.name})"
            button = tk.Button(self.scroll_frame, text=text, command=lambda project=project: self._select_project(project))
            button.pack(pady=5, padx=15, fill='x')

    def _display_no_projects_message(self):
        label = tk.Label(self.scroll_frame, text="You don't have any projects")
        label.pack(pady=10)
        ok_button = tk.Button(self.scroll_frame, text="OK", command=self.root.destroy)
        ok_button.pack(pady=5)

    def _select_project(self, project):
        self.selected_project = project
        self.root.destroy()