from pynput.keyboard import Controller, Key
from enum import Enum
from time import sleep

class KbButton(Enum):
    CAMERA_WIDE   = '1'
    CAMERA_ZOOM   = '2'
    CAMERA_IR     = '3'
    PICTURE       = 'f'
    ANNOTATION    = 't'
    PAUSE         = Key.space

class KbAxis(Enum):
    PITCH         = ('w', 's')
    ROLL          = ('d', 'a')
    YAW           = ('e', 'q')
    THROTTLE      = ('c', 'z')
    CAMERA_PITCH  = (Key.down, Key.up)
    CAMERA_YAW    = (Key.right, Key.left)

class KeyboardEmulator:
    def __init__(self, emulate_hardware=True, print_events=True):
        self.keyboard = Controller()
        self.emulate_hardware = emulate_hardware
        self.print_events = print_events
        
        # 1. Automatically generate active_keys from the Axis Enum
        # We also add the static keys for one-shot buttons
        # self.active_keys = {'1': False, '2': False, '3': False, 'f': False, 't': False}
        self.active_keys = {}

        for button in KbButton:
            key = button.value
            self.active_keys[key] = False
            
        for axis in KbAxis:
            pos_key, neg_key = axis.value
            self.active_keys[pos_key] = False
            self.active_keys[neg_key] = False

    def _press(self, key):
        if self.print_events: print(f'[PRESS]: {key}')
        if self.emulate_hardware: self.keyboard.press(key)

    def _release(self, key):
        if self.print_events: print(f'[RELEASE]: {key}')
        if self.emulate_hardware: self.keyboard.release(key)

    def set_key_state(self, key, should_be_pressed):
        is_currently_pressed = self.active_keys.get(key, False)
        if should_be_pressed and not is_currently_pressed:
            self._press(key)
            self.active_keys[key] = True
        elif not should_be_pressed and is_currently_pressed:
            self._release(key)
            self.active_keys[key] = False

    # 2. Simplified handle_axis using the Enum
    def handle_axis(self, axis_enum: KbAxis, axis_value):
        """Maps a float value to the keys defined in the Axis Enum."""
        key_pos, key_neg = axis_enum.value
        
        if axis_value > 0:
            self.set_key_state(key_pos, True)
            self.set_key_state(key_neg, False)
        elif axis_value < 0:
            self.set_key_state(key_neg, True)
            self.set_key_state(key_pos, False)
        else:
            self.set_key_state(key_pos, False)
            self.set_key_state(key_neg, False)

    def tap(self, button_enum: KbButton, delay=0.08):
        """One-shot tap using KbButton Enum."""
        key = button_enum.value
        self._press(key)
        sleep(delay)
        self._release(key)

    def cleanup(self):
        for key, is_pressed in list(self.active_keys.items()):
            if is_pressed:
                self._release(key)
                self.active_keys[key] = False

    def force_cleanup(self):
        """
        Hard reset: Explicitly releases every key in the mapping, 
        regardless of whether the script thinks they are pressed.
        """
        if self.print_events:
            print("\n[EMERGENCY] Force releasing all mapped keys...")
            
        self.keyboard.tap(KbButton.PAUSE.value)
        for key in self.active_keys.keys():
            # We call the internal _release directly to bypass state checks
            try:
                self.keyboard.release(key)
                self.active_keys[key] = False
            except Exception as e:
                # Silently fail if a specific key wasn't actually 'down' in the OS
                pass
        
        if self.print_events:
            print("[CLEANUP] Keyboard reset complete.")


