import pygame
from .base_rc import BaseRemoteController, RCConnectionError

buttons = [
    ['c1', False],
    ['pause', False],
    ['trigger', False],
    ['start_stop', False],
]

class DJIRC3(BaseRemoteController):
    def __init__(self, joystick_index=0, deadzone_threshold_movement=0.1, deadzone_threshold_elevation=0.1):
        super().__init__(buttons, deadzone_threshold_movement=deadzone_threshold_movement, deadzone_threshold_elevation=deadzone_threshold_elevation)
        
        # 1. Initialize Pygame core if not already done
        if not pygame.get_init():
            pygame.init()
            
        # This tells Pygame to ask the OS for the current list of USB devices again.
        if pygame.joystick.get_init():
            pygame.joystick.quit()  # Shutdown the current scan
        pygame.joystick.init()      # Start a fresh scan

        # 3. Check if anything was found before trying to use it
        if pygame.joystick.get_count() == 0:
            raise RCConnectionError("No joysticks detected by OS.")

        try:
            self.js = pygame.joystick.Joystick(joystick_index)
            self.js.init()
            print(f"Connected to: {self.js.get_name()}")
        except pygame.error as e:
            # Re-raise as a generic exception so your main loop catches it
            raise RCConnectionError(f"DJI RC3 not found at index {joystick_index}: {e}")

    def update(self):
        if not self.js:
            return False

        pygame.event.pump()
        
        try:
            # --- Analog Axis Mapping ---
            # Standard DJI RC3 HID Layout
            self.roll     = self.dead_zone_movement(self.js.get_axis(0))
            self.pitch    = self.dead_zone_movement(self.js.get_axis(1))
            self.throttle = self.dead_zone_elevation(self.js.get_axis(2))
            self.yaw      = self.dead_zone_movement(self.js.get_axis(3))

            # --- Digital Button Mapping ---
            self.button1.update(bool(self.js.get_button(0))) # c1
            self.button2.update(bool(self.js.get_button(2))) # pause
            self.button3.update(bool(self.js.get_button(3))) # trigger
            self.button4.update(bool(self.js.get_button(1))) # start_stop

            # --- Switch Mapping ---
            self.sw1 = -1 if bool(self.js.get_button(7)) else 1 if bool(self.js.get_button(6)) else 0 # mode
            self.sw2 = 1 if bool(self.js.get_button(5)) else 0 if bool(self.js.get_button(4)) else -1 # aux

            self.tilt = self.sw2

            return True

        except pygame.error:
            print('pygame.error')
            return False
        
    @property
    def is_connected(self) -> bool:
        import pygame
        pygame.event.pump() 
        try:
            return pygame.joystick.get_count() > 0 and self.js.get_init()
        except:
            return False

    def close(self):
        if self.js:
            self.js.quit()
