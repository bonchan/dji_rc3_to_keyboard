import pygame
from time import sleep
import sys
from pynput.keyboard import Key, Controller
from DJIFPVRemoteController3 import DJIFPVRemoteController3

# --- CONFIGURATION ---
EMULATE_HARDWARE = True
POLLING_RATE = 0.01  # 100Hz for high responsiveness

PRINT_PRESS_RELEASE = True

keyboard = Controller()

# --- STATE TRACKING ---
# Stores whether a key is currently 'pressed' in the OS
active_keys = {
    'w': False, 's': False, 'a': False, 'd': False,
    'q': False, 'e': False, 'c': False, 'z': False,
    Key.up: False, Key.down: False
}

def printpr(value):
    if PRINT_PRESS_RELEASE:
        print(value)

def handle_press_release(key, delay=0.08):
    printpr(f'press: {key}')
    keyboard.press(key)
    sleep(delay)
    printpr(f'release: {key}')
    keyboard.release(key)

def set_key_state(key, should_be_pressed):
    """
    Only sends an OS event if the state actually changes.
    This prevents the 'input buffer flood' that causes lag.
    """
    if not EMULATE_HARDWARE: return

    is_currently_pressed = active_keys.get(key, False)

    if should_be_pressed and not is_currently_pressed:
        printpr(f'press: {key}')
        keyboard.press(key)
        active_keys[key] = True
    elif not should_be_pressed and is_currently_pressed:
        printpr(f'release: {key}')
        keyboard.release(key)
        active_keys[key] = False

def handle_flight_axis(axis_value, key_pos, key_neg):
    """
    Simple binary logic: 
    If tilted positive -> Press Pos / Release Neg
    If tilted negative -> Press Neg / Release Pos
    If neutral -> Release Both
    """
    # Threshold is handled by your class's deadzone (0.2)
    if axis_value > 0:
        set_key_state(key_pos, True)
        set_key_state(key_neg, False)
    elif axis_value < 0:
        set_key_state(key_neg, True)
        set_key_state(key_pos, False)
    else:
        set_key_state(key_pos, False)
        set_key_state(key_neg, False)

def main():
    pygame.init()
    
    # --- 15-SECOND CONNECTION RETRY ---
    connected = False
    for attempt in range(1, 16):
        pygame.joystick.quit()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            connected = True
            break
        sys.stdout.write(f"\r[WAITING] No controller. Attempt {attempt}/15... ")
        sys.stdout.flush()
        sleep(1)

    if not connected:
        print("\n[FAIL] Exiting.")
        return

    js = pygame.joystick.Joystick(0)
    js.init()
    controller = DJIFPVRemoteController3()
    
    last_mode = None
    last_trigger = False
    last_c1 = False

    print(f"\n[READY] Controlling via: {js.get_name()}")

    try:
        while True:
            controller.update_from_joystick(js)

            # Buttons/Modes (One-shot logic)
            if controller.mode != last_mode:
                target = {1: '1', 0: '2', -1: '3'}.get(controller.mode)
                if target:
                    handle_press_release(target)
                last_mode = controller.mode

            if controller.trigger and not last_trigger:
                handle_press_release('f')
            last_trigger = controller.trigger

            if controller.c1 and not last_c1:
                handle_press_release('t')
            last_c1 = controller.c1

            # Flight Axes (Immediate State Tracking)
            handle_flight_axis(controller.pitch, 'w', 's')     
            handle_flight_axis(controller.roll, 'd', 'a')      
            handle_flight_axis(controller.yaw, 'e', 'q')       
            handle_flight_axis(controller.throttle, 'c', 'z')  
            handle_flight_axis(controller.aux, Key.down, Key.up)

            sleep(POLLING_RATE)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Emergency Cleanup
        for k in active_keys.keys():
            printpr(f'release: {k}')
            keyboard.release(k)
        pygame.quit()

if __name__ == "__main__":
    main()