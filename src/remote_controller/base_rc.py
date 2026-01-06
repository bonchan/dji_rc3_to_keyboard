from abc import ABC, abstractmethod
from src.utils.input_logic import ButtonHandler

class BaseRemoteController(ABC):
    """
    Standard interface for DJI Remote Controllers.
    All values are normalized to a float range of -1.0 to 1.0.
    """
    def __init__(self, buttons, deadzone_threshold_movement, deadzone_threshold_elevation, deadzone_threshold_zoom=0.05):

        self.deadzone_threshold_movement = deadzone_threshold_movement
        self.deadzone_threshold_elevation = deadzone_threshold_elevation
        # Umbral específico para evitar que el zoom se mueva solo por ruido del dial
        self.deadzone_threshold_zoom = deadzone_threshold_zoom

        # --- Analog Axes ---
        self.throttle = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.tilt = 0.0
        self.zoom = 0.0  # <--- Nuevo eje para el scroll del mouse

        # --- Mode Switches ---
        self.sw1 = 0
        self.sw2 = 0

        # --- Digital Buttons ---
        self.button1 = ButtonHandler(buttons[0][0], print_update=buttons[0][1])
        self.button2 = ButtonHandler(buttons[1][0], print_update=buttons[1][1])
        self.button3 = ButtonHandler(buttons[2][0], print_update=buttons[2][1])
        self.button4 = ButtonHandler(buttons[3][0], print_update=buttons[3][1])

    @abstractmethod
    def update(self) -> bool:
        pass
    
    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass
    
    def dead_zone_movement(self, value):
        return self._dead_zone(value, self.deadzone_threshold_movement)
    
    def dead_zone_elevation(self, value):
        return self._dead_zone(value, self.deadzone_threshold_elevation)
    
    # Nuevo método para el eje del zoom
    def dead_zone_zoom(self, value):
        return self._dead_zone(value, self.deadzone_threshold_zoom)
    
    def _dead_zone(self, value, threshold):
        return 0.0 if abs(value) < threshold else value

    def __str__(self):
        """Standardized string output for debugging including Zoom."""
        axes = (f"T: {self.throttle: .2f} | Y: {self.yaw: .2f} | "
                f"P: {self.pitch: .2f} | R: {self.roll: .2f} | "
                f"Tilt: {self.tilt: .2f} | Zoom: {self.zoom: .2f}")
        
        btns = f"B1: {int(self.button1)} B2: {int(self.button2)} B3: {int(self.button3)} B4: {int(self.button4)}"
        swts = f"SW1: {self.sw1} SW2: {self.sw2}"
        
        return f"{axes} | {btns} | {swts}"

class RCConnectionError(Exception):
    """Custom exception for DJI Remote Controller connection issues."""
    pass
