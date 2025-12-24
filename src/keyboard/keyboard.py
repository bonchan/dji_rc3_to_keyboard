from pynput.keyboard import Key, Controller
from time import sleep

class KeyboardEmulator:
    def __init__(self, emulate_hardware=True, print_events=True):
        self.keyboard = Controller()
        self.emulate_hardware = emulate_hardware
        self.print_events = print_events
        
        # Track state to prevent "input flooding" (sending press events every frame)
        self.active_keys = {
            'w': False, 's': False, 'a': False, 'd': False,
            'q': False, 'e': False, 'c': False, 'z': False,
            '1': False, '2': False, '3': False,
            'f': False, 't': False,
            Key.up: False, Key.down: False,
            Key.right: False, Key.left: False,
        }

    def _press(self, key):
        if self.print_events:
            print(f'[PRESS]: {key}')
        if self.emulate_hardware:
            self.keyboard.press(key)

    def _release(self, key):
        if self.print_events:
            print(f'[RELEASE]: {key}')
        if self.emulate_hardware:
            self.keyboard.release(key)

    def tap(self, key, delay=0.08):
        """Quickly press and release a key (one-shot)."""
        self._press(key)
        sleep(delay)
        self._release(key)

    def set_key_state(self, key, should_be_pressed):
        """Ensures the key state in the OS matches the desired state."""
        is_currently_pressed = self.active_keys.get(key, False)

        if should_be_pressed and not is_currently_pressed:
            self._press(key)
            self.active_keys[key] = True
        elif not should_be_pressed and is_currently_pressed:
            self._release(key)
            self.active_keys[key] = False

    def handle_axis(self, axis_value, key_pos, key_neg):
        """Maps a float axis (-1.0 to 1.0) to two binary keys."""
        if axis_value > 0:
            self.set_key_state(key_pos, True)
            self.set_key_state(key_neg, False)
        elif axis_value < 0:
            self.set_key_state(key_neg, True)
            self.set_key_state(key_pos, False)
        else:
            self.set_key_state(key_pos, False)
            self.set_key_state(key_neg, False)

    def cleanup(self):
        """Release all keys - call this on exit!"""
        for key, is_pressed in self.active_keys.items():
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