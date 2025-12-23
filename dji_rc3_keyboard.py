import pygame
from time import sleep
from pynput.keyboard import Key, Controller

# Assuming your DJIFPVRemoteController3 class is in the same directory
from DJIFPVRemoteController3 import DJIFPVRemoteController3

# --- CONFIGURATION ---
EMULATE_HARDWARE = True
HIGH_SPEED_THRESHOLD = 0.1  # Above this, key is held solid. Below this, it pulses.
PULSE_DURATION = 0.13       # Duration of the "tap" for low sensitivity
PULSE_DURATION_VERTICAL = 0.03  # Duration of the "tap" for vertical axis
PULSE_DURATION_PITCH = 0.02     # Duration of the "tap" for camera pitch axis
POLLING_RATE = 0.1         # 100Hz loop speed for responsiveness

# Initialize Keyboard
keyboard = Controller()

def press_release(key, duration=0.05):
    """Helper to press and release a key with a delay."""
    keyboard.press(key)
    sleep(duration)
    keyboard.release(key)

def handle_flight_axis(axis_value, key_pos, key_neg, pulse_duration=PULSE_DURATION):
    """
    Handles the pulsing logic for analog-to-digital emulation.
    If the value is 0.0 (already handled by your class deadzone), it releases keys.
    """
    if not EMULATE_HARDWARE:
        return

    # Case 1: Stick is Neutral (Value is 0.0 due to your dead_zone function)
    if axis_value == 0:
        keyboard.release(key_pos)
        keyboard.release(key_neg)
        return

    # Determine direction
    target_key = key_pos if axis_value > 0 else key_neg
    opposite_key = key_neg if axis_value > 0 else key_pos

    # Safety: Release the opposite direction
    keyboard.release(opposite_key)

    # Case 2: Move the drone
    keyboard.press(target_key)
    
    # Sensitivity Logic: If stick is tilted but not floored, 
    # release it quickly to create a 'slow' movement.
    if abs(axis_value) < HIGH_SPEED_THRESHOLD:
        sleep(pulse_duration)
        keyboard.release(target_key)
    # If it is > HIGH_SPEED_THRESHOLD, we don't release here.
    # It stays 'pressed' until the next loop iteration or stick return.

def main():
    pygame.init()

    connected = False
    for attempt in range(1, 16):
        pygame.joystick.quit() # Refresh the joystick module
        pygame.joystick.init()
        
        count = pygame.joystick.get_count()
        if count > 0:
            print(f"\n[SUCCESS] Controller detected on attempt {attempt}!")
            connected = True
            break
        else:
            # Print on the same line to keep the console clean
            print(f"\r[RETRY] No controller found. Attempt {attempt}/15... (Turn it on now)")
            sleep(1)

    if not connected:
        print("\n\n[FAIL] No DJI Controller found after 15 seconds. Exiting.")
        return

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Connected to: {js.get_name()}")

    controller = DJIFPVRemoteController3()

    # Track states for buttons/switches to prevent spamming
    last_mode = None
    last_trigger = False
    last_c1 = False

    print("Control Loop Active. Press Ctrl+C to exit.")

    try:
        while True:
            # 1. Update controller state
            controller.update_from_joystick(js)

            # 2. Handle Mode Switches (1, 2, 3)
            if controller.mode != last_mode:
                mode_map = {1: '1', 0: '2', -1: '3'}
                target_key = mode_map.get(controller.mode)
                if target_key:
                    press_release(target_key)
                last_mode = controller.mode

            # 3. Handle Trigger (F)
            if controller.trigger and not last_trigger:
                press_release('f')
            last_trigger = controller.trigger

            # 3. Handle C1 (T)
            if controller.c1 and not last_c1:
                press_release('t')
            last_c1 = controller.c1

            # 4. Handle Flight Axes with PWM Sensitivity
            # Pitch
            handle_flight_axis(controller.pitch, 'w', 's')
            # Roll
            handle_flight_axis(controller.roll, 'd', 'a')
            # Yaw
            handle_flight_axis(controller.yaw, 'e', 'q')
            # Yaw
            handle_flight_axis(controller.yaw, Key.right, Key.left)
            # Vertical
            handle_flight_axis(controller.throttle, 'c', 'z', pulse_duration=PULSE_DURATION_VERTICAL)
            # Camera Aux
            handle_flight_axis(controller.aux, Key.down, Key.up, pulse_duration=PULSE_DURATION_PITCH)

            # 5. Maintain high polling frequency
            sleep(POLLING_RATE)

    except KeyboardInterrupt:
        print("\nStopping controller emulation...")
    finally:
        # Emergency release of all keys on exit
        for k in ['w','s','a','d','q','e','c','z','f','t','1','2','3']:
            keyboard.release(k)
        keyboard.release(Key.up)
        keyboard.release(Key.down)

if __name__ == "__main__":
    main()