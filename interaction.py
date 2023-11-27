from core import Rectangle, ImageCanvas

class UserInteraction:
    def __init__(self, canvas):
        """
        Initialize UserInteraction with a reference to the ImageCanvas.

        :param canvas: The ImageCanvas instance where interactions take place.
        """
        self.canvas = canvas
        self.selected_rectangle = None
        self.mode = 'normal'  # Can be 'normal', 'drawing', 'moving', 'rotating', etc.

    def handleClick(self, x, y):
        """
        Handle a click event at the specified coordinates.

        :param x: The x-coordinate of the click.
        :param y: The y-coordinate of the click.
        """
        pass

    def handleDrag(self, start_x, start_y, end_x, end_y):
        """
        Handle a drag event from start to end coordinates.

        :param start_x: The starting x-coordinate.
        :param start_y: The starting y-coordinate.
        :param end_x: The ending x-coordinate.
        :param end_y: The ending y-coordinate.
        """
        pass

    def handleRotate(self, center_x, center_y, angle):
        """
        Handle a rotate action around a center point.

        :param center_x: The x-coordinate of the center point.
        :param center_y: The y-coordinate of the center point.
        :param angle: The angle of rotation.
        """
        pass

    def switchMode(self, new_mode):
        """
        Switch the interaction mode.

        :param new_mode: The new mode to switch to.
        """
        pass

class InputHandler:
    def __init__(self, user_interaction):
        """
        Initialize InputHandler with a reference to UserInteraction.

        :param user_interaction: The UserInteraction instance to handle inputs for.
        """
        self.user_interaction = user_interaction

    def processClickEvent(self, event):
        """
        Process a mouse click event.

        :param event: The event object containing event details.
        """
        pass

    def processDragEvent(self, event):
        """
        Process a mouse drag event.

        :param event: The event object containing event details.
        """
        pass

    def processRotateEvent(self, event):
        """
        Process a mouse rotate event (like mouse wheel or right-click drag).

        :param event: The event object containing event details.
        """
        pass

    # Additional methods for handling different types of events
