from core import ImageCanvas
from persistence import DatabaseManager
from enum import Enum, auto
from typing import Tuple, Optional
import tkinter as tk


class Mode(Enum):
    DRAWING = auto()
    MOVING = auto()
    ROTATING = auto()
    IDLE = auto()


class UserInteraction:
    def __init__(self, canvas: ImageCanvas, db_manager: DatabaseManager):
        self.canvas: ImageCanvas = canvas
        self.db_manager: DatabaseManager = db_manager
        self.current_mode = Mode.IDLE
        self.start_point: Optional[Tuple[int, int]] = None

    def handleLClick(self, x: int, y: int):
        if self.current_mode == Mode.IDLE:
            rectangle_found = self.canvas.get_selected_rectangle(x, y)
            if rectangle_found:
                self.current_mode = Mode.MOVING
            else:
                self.start_point = (x, y)
                self.current_mode = Mode.DRAWING
        elif self.current_mode == Mode.DRAWING:
            self.complete_drawing(x, y)
            self.current_mode = Mode.IDLE

    def handleRClick(self, x: int, y: int):
        if self.current_mode == Mode.IDLE:
            rectangle_found = self.canvas.get_selected_rectangle(x, y)
            if rectangle_found:
                self.current_mode = Mode.ROTATING
    
    def complete_drawing(self, x: int, y: int):
        if self.start_point:
            self.canvas.add_rectangle(start_point=self.start_point, end_point=(x, y))
            self.start_point = None
            self.current_mode = Mode.IDLE

    def handleMouseMove(self, x: int, y: int):
        if self.current_mode == Mode.MOVING:
            self.canvas.move_selected_rectangle(x, y)
        elif self.current_mode == Mode.ROTATING:
            self.canvas.rotate_selected_rectangle(x, y)
        self.canvas.update_canvas() 

    def handleMouseRelease(self, x: int, y: int):
        if self.current_mode in [Mode.MOVING, Mode.ROTATING]:
            self.canvas.complete_rectangle()
            self.current_mode = Mode.IDLE


class InputHandler:
    def __init__(self, user_interaction):
        """
        Initialize InputHandler with a reference to UserInteraction.

        :param user_interaction: The UserInteraction instance to handle inputs for.
        """
        self.user_interaction: UserInteraction = user_interaction

    def processLClickEvent(self, event: tk.Event):
        self.user_interaction.handleLClick(event.x, event.y)

    def processRClickEvent(self, event: tk.Event):
        self.user_interaction.handleRClick(event.x, event.y)

    def processMouseMoveEvent(self, event: tk.Event):
        self.user_interaction.handleMouseMove(event.x, event.y)

    def processMouseReleaseEvent(self, event: tk.Event):
        self.user_interaction.handleMouseRelease(event.x, event.y)