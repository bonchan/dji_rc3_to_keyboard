import time

class ButtonHandler:
    def __init__(self, button_name, long_threshold=1.0, print_update=False):
        self.button_name = button_name
        self.long_threshold = long_threshold
        self.print_update = print_update

        self.last_state = False
        self.start_time = 0
        self.long_press_triggered = False  # The latch

        self.is_pressed = False
        self.is_short_tap = False
        self.is_long_press = False
        self.is_maintained_long_press = False

    def update(self, current_val: bool):
        current_time = time.time()
        self.is_pressed = current_val
        self.is_short_tap = False
        self.is_long_press = False
        # Note: We don't reset is_maintained_long_press to False here yet 
        # because we need to calculate its state based on current_val

        if current_val:  # Button is DOWN
            if not self.last_state:  # First frame of press
                self.start_time = current_time
                self.long_press_triggered = False 
            
            # Check for Long Press
            if current_time - self.start_time >= self.long_threshold:
                # 1. Maintained state: Always True once threshold is crossed
                self.is_maintained_long_press = True
                
                # 2. One-shot state: Only True on the exact frame it crosses
                if not self.long_press_triggered:
                    self.is_long_press = True
                    self.long_press_triggered = True
        else:  # Button is UP
            if self.last_state:  # Just released
                if not self.long_press_triggered:
                    self.is_short_tap = True
                
                self.start_time = 0
                self.long_press_triggered = False
            
            # Reset maintained state when button is released
            self.is_maintained_long_press = False

        self.last_state = current_val

        if self.print_update:
            print(f'{self.button_name} - is_pressed: {self.is_pressed} | is_short_tap: {self.is_short_tap} | is_long_press: {self.is_long_press} | is_maintained_long_press: {self.is_maintained_long_press}')