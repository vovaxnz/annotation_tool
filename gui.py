import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from labeling import ImageCanvas
from interaction import UserInteraction, InputHandler


class MainWindow(tk.Tk):
    def __init__(self, canvas: ImageCanvas, user_interaction: UserInteraction):
        super().__init__()
        self.title("Rectangle Drawing Tool")
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Set window size to screen size
        self.geometry(f"{screen_width}x{screen_height}+0+0")

        self.canvas_view = CanvasView(self, canvas, user_interaction, height=screen_height, width=screen_width)
        self.control_panel = ControlPanel(self)
        self.canvas_view.pack(side="left", fill="both", expand=True)
        self.control_panel.pack(side="right", fill="y")

class CanvasView(tk.Canvas):
    def __init__(self, parent, canvas: ImageCanvas, user_interaction: UserInteraction, height: int, width: int):
        super().__init__(parent, bg="black") 
        self.height, self.width = height, width
        self.image_canvas = canvas
        self.user_interaction = user_interaction
        self.input_handler = InputHandler(self.user_interaction)
        self.bind("<Button-1>", self.input_handler.processLClickEvent)
        self.bind("<Button-2>", self.input_handler.processMClickEvent)
        self.bind("<Button-3>", self.input_handler.processRClickEvent)
        self.bind("<B1-Motion>", self.input_handler.processMouseMoveEvent)
        self.bind("<B3-Motion>", self.input_handler.processMouseMoveEvent)
        self.bind("<ButtonRelease-1>", self.input_handler.processMouseReleaseEvent)
        self.bind("<ButtonRelease-3>", self.input_handler.processMouseReleaseEvent)
        # Set focus to the canvas to receive keyboard events
        self.focus_set()
        self.bind("<e>", self.input_handler.processEPressEvent)
        self.bind("<q>", self.input_handler.processQPressEvent)
        self.bind("<w>", self.input_handler.processWPressEvent)

        # Drawing loop to update the canvas
        self.after(100, self.update_canvas)

        # TODO: Add zoom

    def update_canvas(self):
        # Convert the OpenCV image to a format suitable for Tkinter
        cv_image = cv2.cvtColor(self.image_canvas.canvas, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(cv_image)
        tk_image = ImageTk.PhotoImage(image=pil_image)

        # Clear the current contents of the canvas
        self.delete("all")

        # Add new image to the canvas
        self.create_image(0, 0, anchor="nw", image=tk_image)

        # Keep a reference to the image to prevent garbage collection
        self.tk_image = tk_image

        self.after(100, self.update_canvas)

class ControlPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)