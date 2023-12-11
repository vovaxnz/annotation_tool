from labeling import LabelingApp, Mode
import tkinter as tk

class UserInteraction:
    def __init__(self, labeling_app: LabelingApp):
        self.app: LabelingApp = labeling_app

    def handleLClick(self, x: int, y: int):
        if self.app.canvas.mode == Mode.IDLE:
            rect_id = self.app.canvas.get_selected_rectangle(x, y)
            if rect_id is not None:
                self.app.canvas.mode = Mode.MOVING
            else:
                self.app.canvas.start_point = (x, y)
                self.app.canvas.mode = Mode.DRAWING
        elif self.app.canvas.mode == Mode.DRAWING:
            self.app.canvas.complete_drawing(x, y)
            self.app.canvas.mode = Mode.IDLE

    def handleRClick(self, x: int, y: int):
        if self.app.canvas.mode == Mode.IDLE:
            rect_id = self.app.canvas.get_selected_rectangle(x, y)
            if rect_id is not None:
                self.app.canvas.mode = Mode.ROTATING
    
    def handleMClick(self, x: int, y: int):
        self.app.canvas.remove_rectangle(x, y)
        self.app.canvas.mode = Mode.IDLE

    def handleMouseMove(self, x: int, y: int):
        if self.app.canvas.mode == Mode.MOVING:
            self.app.canvas.move_selected_rectangle(x, y)
        elif self.app.canvas.mode == Mode.ROTATING:
            self.app.canvas.rotate_selected_rectangle(x, y)
        self.app.canvas.update_canvas() 

    def handleMouseRelease(self, x: int, y: int):
        if self.app.canvas.mode in [Mode.MOVING, Mode.ROTATING]:
            self.app.canvas.complete_rectangle()
            self.app.canvas.mode = Mode.IDLE

    def handle_e(self): 
        self.app.export_data("result.json")

    def handle_q(self): 
        self.app.backward()

    def handle_w(self): 
        self.app.forward()

        
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

    def processMClickEvent(self, event: tk.Event):
        self.user_interaction.handleMClick(event.x, event.y)

    def processMouseMoveEvent(self, event: tk.Event):
        self.user_interaction.handleMouseMove(event.x, event.y)

    def processMouseReleaseEvent(self, event: tk.Event):
        self.user_interaction.handleMouseRelease(event.x, event.y)

    def processEPressEvent(self, event: tk.Event):
        self.user_interaction.handle_e()

    def processQPressEvent(self, event: tk.Event):
        self.user_interaction.handle_q()

    def processWPressEvent(self, event: tk.Event):
        self.user_interaction.handle_w()