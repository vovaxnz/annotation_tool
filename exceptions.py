import tkinter as tk
import sys
import traceback
from tkinter import scrolledtext 


class MessageBoxException(Exception):
    def __init__(self, message):
        self.message = message
        self.root = tk.Tk()
        self.root.title("Error")

        # Create a Text widget with a vertical scrollbar
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)  # Make it expand and fill space
        self.text_area.insert(tk.INSERT, message)
        self.text_area.config(state=tk.DISABLED)  # Make the text read-only

        # Button to close the window
        self.close_button = tk.Button(self.root, text="Close", command=self.close_window)
        self.close_button.pack(pady=5, fill=tk.X)  # Optional: Make the button expand horizontally

        self.root.protocol("WM_DELETE_WINDOW", self.close_window)  # Handle window close button
        self.root.mainloop()

    def close_window(self):
        self.root.destroy()
        super().__init__(self.message)
        sys.exit(1)  # Exit the program


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    This function is called when an exception is raised and it is not caught anywhere.
    It shows the exception information in a messagebox instead of the console.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # If it's a keyboard interrupt, exit without showing the message box.
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    raise MessageBoxException(err_msg)

# Set sys.excepthook to our custom function to catch all unhandled exceptions
sys.excepthook = handle_exception