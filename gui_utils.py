import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from typing import Callable, List
from config import settings
from models import ProjectData
from tkinter import ttk
import tkinterweb



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
        elif value['type'] == 'boolean':
            self.create_toggle_widget(key, value, row)

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

    def create_toggle_widget(self, key, value, row):
        var = tk.BooleanVar()
        var.set(bool(value['value']))

        style = ttk.Style()
        style.configure('Big.TCheckbutton', indicatorsize=30, padding=10)

        check = ttk.Checkbutton(self.root, variable=var, style='Big.TCheckbutton')
        check.grid(row=row, column=1, padx=10, pady=5, sticky=tk.W)

        self.widgets[key] = var

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


class IdForm:
    def __init__(self, root: tk.Tk = None, max_id: int = None):
        self.root = tk.Toplevel(root)
        self.root.title("Enter item ID")
        self.max_id = max_id  # Store the maximum ID allowed
        
        ttk.Label(self.root, text="Item ID:").grid(row=0, column=0, padx=20, pady=10)

        # Validation command setup
        vcmd = (self.root.register(self.validate_input), '%P')  # %P passes the value of the entry if the edit is allowed

        self.entry = ttk.Entry(self.root, width=40, validate='key', validatecommand=vcmd)
        self.entry.grid(row=0, column=1, padx=20, pady=10)

        save_button = ttk.Button(self.root, text="Go", command=self.on_save)
        save_button.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E, padx=20, pady=10)

        self.item_id = None

    def on_save(self):
        if self.entry.get():
            self.item_id = int(self.entry.get())  # Convert to int since we know it's a valid integer
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

    def get_id(self):
        self.root.wait_window()
        return self.item_id
    

class ProjectSelector:
    def __init__(self, projects: List[ProjectData], root: tk.Tk, title: str = None, description: str = None):
        self.projects = projects
        self.selected_project = None
        self.parent = root
        self.title = "Select Project" if title is None else title
        self.description = "Select Project" if description is None else description

    def select(self):
        self.root = tk.Toplevel(self.parent)
        self.root.title(self.title)

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

        self.text = tk.Label(self.root, text=self.description, justify='left')
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


class MessageBox:
    def __init__(self, message):
        self.root = tk.Tk()
        self.root.title("Update result")

        # Create a Text widget with a vertical scrollbar
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.text_area.insert(tk.INSERT, message)
        self.text_area.config(state=tk.DISABLED)  # Start as disabled to prevent editing

        # Enable text selection and copying while disabling editing
        self.text_area.bind("<Button-1>", self.enable_selection)

        # Button to close the window
        self.close_button = tk.Button(self.root, text="Ok", command=self.close_window)
        self.close_button.pack(pady=5, fill=tk.X)

        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.mainloop()

    def enable_selection(self, event):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.root.after(1, self.disable_editing)

    def disable_editing(self):
        self.text_area.config(state=tk.DISABLED)

    def close_window(self):
        self.root.destroy()

def show_html_window(root: tk.Tk, title, html_content):
    window = tk.Toplevel(root)
    window.title(title)

    html_frame = tkinterweb.HtmlFrame(window, messages_enabled=False)
    html_frame.load_html(html_content)
    html_frame.pack(fill="both", expand=True)

    window.update_idletasks()
    window.update()
