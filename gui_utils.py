import tkinter as tk
from tkinter import ttk
from config import settings


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
    def __init__(self, root: tk.Tk = None, message: str = None):
        if root is not None:
            self.root = tk.Toplevel(root)
        else:
            self.root = tk.Tk()
        self.root.title("Settings Manager")
        self.message = message
        self.setup_gui()

        if root is None:
            self.root.mainloop()
        
    def setup_gui(self):
        labels = sorted(settings.data.keys())
        self.entries = {}
        row_offset = 0
        if self.message is not None:
            message_label = ttk.Label(self.root, text=self.message)
            message_label.grid(row=0, column=0, columnspan=2, padx=20, pady=10)
            row_offset = 1

        for i, label in enumerate(labels):
            ttk.Label(self.root, text=label).grid(row=i + row_offset, column=0, padx=20, pady=10)
            entry = ttk.Entry(self.root, width=40)
            entry.grid(row=i + row_offset, column=1, padx=20, pady=10)
            value = settings.data.get(label, '')
            value = "" if value is None else value
            entry.insert(0, value)
            self.entries[label] = entry

        save_button = ttk.Button(self.root, text="Save", command=self.on_save)
        save_button.grid(row=len(labels) + row_offset, column=1, sticky=tk.W+tk.E, padx=20, pady=10)

        
    def on_save(self):
        for key, entry in self.entries.items():
            settings.data[key] = entry.get()
        settings.save_settings()
        self.root.destroy()