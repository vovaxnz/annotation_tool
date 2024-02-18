import tkinter as tk
from tkinter import messagebox
import sys


class MessageBoxException(Exception):
    def __init__(self, message):
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        messagebox.showerror("Error", message)
        root.destroy()
        super().__init__(message)
        sys.exit(1)  # Exit the program