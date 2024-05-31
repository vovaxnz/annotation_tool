import tkinter as tk
from tkinter import ttk
from typing import Callable, List
from config import settings
from labeling.abstract_labeling_app import ProjectData
from labeling.annotation import AnnotationApp
from labeling.filtering import FilteringApp
from tkinter import ttk
from tkinter import font



def get_loading_window(text: str, root: tk.Tk):
    root = tk.Toplevel(root)
    root.title("Loading")

    # Set window size
    window_width = 300
    window_height = 100

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate x and y coordinates for the Tk root window
    x = (screen_width/2) - (window_width/2)
    y = (screen_height/2) - (window_height/2)

    # Set the dimensions of the window and where it is placed
    root.geometry('%dx%d+%d+%d' % (window_width, window_height, x, y))

    # Create a label with text "Waiting" that is centered
    label = tk.Label(root, text=text)
    label.pack(expand=True)

    # Start the tkinter main event loop in a non-blocking way
    root.update_idletasks()
    root.update()
    return root



class SettingsManager:
    def __init__(self, root: tk.Tk = None, at_exit: Callable = None):
        
        self.root = tk.Toplevel(root) if root else tk.Tk()
        self.root.title("Settings Manager")
        self.widgets = {}
        
        self.setup_gui()
        
        self.at_exit = at_exit

        if not root:
            self.root.mainloop()

    def setup_gui(self):
        row_offset = 0
        for key, value in settings.data.items():
            if isinstance(value, dict) and 'type' not in value:
                self.create_header(key, row_offset)
                row_offset += 1
                row_offset = self.create_nested_widgets(value, row_offset, key)
            else:
                self.create_widget(key, value, row_offset)
                row_offset += 1

        self.create_save_button(row_offset)

    def create_header(self, key, row):
        ttk.Label(self.root, text=key.capitalize(), font=('Arial', 12, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 0)
        )

    def create_nested_widgets(self, data, start_row, parent_key):
        for key, value in data.items():
            full_key = f"{parent_key}.{key}"
            self.create_widget(full_key, value, start_row)
            start_row += 1
        return start_row

    def create_widget(self, key, value, row):
        ttk.Label(self.root, text=key.split('.')[-1].replace('_', ' ').capitalize()).grid(
            row=row, column=0, sticky=tk.W, padx=10, pady=5
        )
        if value['type'] == 'string':
            self.create_entry_widget(key, value, row)
        elif value['type'] == 'number':
            self.create_scale_widget(key, value, row)

    def create_entry_widget(self, key, value, row):
        entry = ttk.Entry(self.root)
        entry.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W + tk.E)
        if value['value']:
            entry.insert(0, value['value'])
        self.widgets[key] = entry

    def create_scale_widget(self, key, value, row):
        scale_var = tk.DoubleVar()
        if value['value'] is not None:
            scale_var.set(value['value'])
        scale = tk.Scale(
            self.root, from_=value['min'], to=value['max'], orient='horizontal', variable=scale_var, resolution=value['step']
        )
        scale.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W + tk.E)
        self.widgets[key] = scale_var

    def create_save_button(self, row):
        save_button = ttk.Button(self.root, text="Save", command=self.on_save)
        save_button.grid(
            row=row, column=1, sticky=tk.W + tk.E, padx=20, pady=10
        )

    def on_save(self):
        for key, widget in self.widgets.items():
            value = widget.get()
            if "." in key:
                keys = key.split('.')
                assert (len(keys) == 2)
                settings.data[keys[0]][keys[1]]['value'] = value
            else:
                settings.data[key]['value'] = value
        settings.save_settings()
        if self.at_exit is not None:
            self.at_exit()
        self.root.destroy()


class ImageIdForm:
    def __init__(self, root: tk.Tk = None, max_id: int = None):
        self.root = tk.Toplevel(root)
        self.root.title("Enter image ID")
        self.max_id = max_id  # Store the maximum ID allowed
        
        ttk.Label(self.root, text="Image ID:").grid(row=0, column=0, padx=20, pady=10)

        # Validation command setup
        vcmd = (self.root.register(self.validate_input), '%P')  # %P passes the value of the entry if the edit is allowed

        self.entry = ttk.Entry(self.root, width=40, validate='key', validatecommand=vcmd)
        self.entry.grid(row=0, column=1, padx=20, pady=10)

        save_button = ttk.Button(self.root, text="Go", command=self.on_save)
        save_button.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E, padx=20, pady=10)

        self.image_id = None

    def on_save(self):
        if self.entry.get():
            self.image_id = int(self.entry.get())  # Convert to int since we know it's a valid integer
        self.root.destroy()

    def validate_input(self, value_if_allowed):
        if value_if_allowed == "":
            return True  # Allow clearing the entry field
        try:
            value = int(value_if_allowed)
            if 0 < value <= self.max_id:
                return True  # Return True if the value is an integer and less than max_id
            else:
                return False  # Return False if the value exceeds max_id
        except ValueError:
            return False  # Return False if the value_if_allowed is not an integer

    def get_image_id(self):
        self.root.wait_window()
        return self.image_id
    

class AnnotationStatusBar(tk.Frame):
    def __init__(self, parent, app: AnnotationApp, **kw):
        super().__init__(parent, **kw)
        self.app: AnnotationApp = app

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


class FilteringStatusBar(tk.Frame):
    def __init__(self, parent, app: FilteringApp, **kw):
        super().__init__(parent, **kw)
        self.app: FilteringApp = app

        # Create labels within the status bar
        self.mode_label = tk.Label(self, bd=1)
        self.delay_label = tk.Label(self, bd=1)
        self.selected_label = tk.Label(self, bd=1)
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
        
        self.delay_label.grid(row=0, column=2, sticky='ew', padx=15)
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=3, sticky='ns')
        
        self.selected_label.grid(row=0, column=4, sticky='ew', padx=15)
        sep2 = ttk.Separator(self, orient='vertical')
        sep2.grid(row=0, column=5, sticky='ns')
        
        self.img_id_label.grid(row=0, column=6, sticky='ew', padx=15)
        sep5 = ttk.Separator(self, orient='vertical')
        sep5.grid(row=0, column=7, sticky='ns')
        
        self.speed_label.grid(row=0, column=8, sticky='ew', padx=15)
        sep6 = ttk.Separator(self, orient='vertical')
        sep6.grid(row=0, column=9, sticky='ns')
        
        self.processed_label.grid(row=0, column=10, sticky='ew', padx=15)
        sep7 = ttk.Separator(self, orient='vertical')
        sep7.grid(row=0, column=11, sticky='ns')
        
        self.progress_bar.grid(row=0, column=12, sticky='ew', padx=15)
        self.columnconfigure(12, weight=1)  # Make progress bar expand
        sep8 = ttk.Separator(self, orient='vertical')
        sep8.grid(row=0, column=13, sticky='ns')

        self.duration_label.grid(row=0, column=14, sticky='ew', padx=15)
        sep9 = ttk.Separator(self, orient='vertical')
        sep9.grid(row=0, column=15, sticky='ns')

    def on_resize(self, event):
        # Calculate an appropriate font size based on the current width
        new_font_size = max(8, min(15, int(self.winfo_width() / 130))) 
        label_font = font.Font(family="Ubuntu Condensed", size=new_font_size)
        
        # Set the new font to all labels and progress bar
        for widget in [self.mode_label, self.delay_label, self.selected_label, self.img_id_label, self.speed_label, self.processed_label, self.duration_label]:
            widget.config(font=label_font)

    def update_status(self):
        status_data = self.app.status_data 
        
        # Update labels
        self.mode_label.config(text=f"Mode: Filtering")

        self.delay_label.config(text=f"Delay: {status_data.delay}")

        selected_text = "Selected: TRUE" if status_data.selected else "Selected: FALSE"
        selected_color = "lime" if status_data.selected else "gray"
        self.selected_label.config(text=selected_text, bg=selected_color)

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