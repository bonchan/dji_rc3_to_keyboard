import time
import argparse
import serial.tools.list_ports
from src.remote_controller.dji_rc3 import DJIRC3
from src.remote_controller.dji_rcN1 import DJIRCN1
from src.remote_controller.dji_m300 import DJIM300
from src.remote_controller.base_rc import RCConnectionError

from src.utils.sequence import SequenceHandler, SequenceStep
from src.keyboard.keyboard import KeyboardEmulator, KbAxis, KbButton



def main(model_choice):
    print(f"--- DJI Universal Interface | Target: {model_choice} ---")

    rc = None
    retry_limit = 15

    for retry in range(retry_limit):
        try:
            if model_choice == 'RC3':
                rc = DJIRC3(joystick_index=0, deadzone_threshold_movement=0.3, deadzone_threshold_elevation=0.6)
            elif model_choice == 'M300':
                rc = DJIM300()
            elif model_choice == 'N1':
                rc = DJIRCN1()
            
            # If we reach this line, constructor succeeded
            print(f"Successfully connected to {model_choice}!")
            break 
            
        except RCConnectionError as e:
            rc = None
            print(f"Retrying... [{retry}/{retry_limit}] {e}")
            time.sleep(1)

    k_emu = KeyboardEmulator(emulate_hardware=True, print_events=True)

    seq_handler = SequenceHandler()
    cross_and_turn = [
        SequenceStep(duration=3.0, axes_map={KbAxis.PITCH: 1.0, KbAxis.YAW: 0.0}), # Cross
        SequenceStep(duration=0.1, axes_map={KbButton.PAUSE: True}), # Wait
        SequenceStep(duration=8.0, axes_map={KbAxis.PITCH: 0.0, KbAxis.YAW: 1.0}), # Turn 180
    ]


    last_camera = None

    # State toggles
    hold_cruise = False  # Locks Pitch
    hold_turn = False    # Locks Yaw
    seq_running = False

    # Values to store when hold is activated
    frozen_pitch = 0.0
    frozen_roll = 0.0
    frozen_yaw = 0.0

    # 3. Universal loop
    try:
        print("Streaming data. Press Ctrl+C to stop.")
        while True:
            if not rc.is_connected:
                print("[!!!] CONTROLLER DISCONNECTED [!!!]")
                break

            if not rc.update(): continue

            if rc.button1.is_short_tap:
                print('>>> Emergency PAUSE for 3 sec <<<')
                seq_handler.stop()
                k_emu.force_cleanup()
                hold_cruise = False
                hold_turn = False
                time.sleep(3)
                print('>>> Emergency PAUSE Finished <<<')
                continue

            if rc.button3.is_long_press and not (hold_cruise or hold_turn):
                if seq_running:
                    seq_handler.stop()
                else:
                    seq_handler.start_sequence(cross_and_turn)

            overrides, seq_running = seq_handler.update()
            
            if not seq_running:
                # --- enable cruise ---
                if rc.button4.is_short_tap:
                    if hold_cruise:
                        print('>>> DISABLE CRUISE <<<')
                        hold_cruise = False
                    else:
                        if hold_turn:
                            print('>>> DISABLE TURN <<<')
                            hold_turn = False
                        elif rc.yaw != 0:
                            print('>>> ENABLE TURN <<<')
                            frozen_yaw = rc.yaw
                            hold_turn = True

                if rc.button1.is_maintained_long_press and rc.button4.is_short_tap:
                    print('>>> ENABLE FORWARD CRUISE <<<')
                    hold_cruise = True
                    frozen_pitch = 1
                    frozen_roll = 0

                if rc.button4.is_long_press:
                    if rc.pitch != 0 or rc.roll != 0:
                        print('>>> ENABLE FREE CRUISE <<<')
                        hold_cruise = True
                        frozen_pitch = rc.pitch
                        frozen_roll = rc.roll
                    else:
                        print('>>> FREE CRUISE HAS NO VALUES TO CRUISE<<<')

            

            # --- Determine Final Axis Values ---
            # If Cruise is on, use the frozen pitch, otherwise use real-time stick
            pitch_val = frozen_pitch if hold_cruise else overrides.get(KbAxis.PITCH, rc.pitch)
            
            # Roll remains real-time unless you want to lock that too
            roll_val = frozen_roll if hold_cruise else overrides.get(KbAxis.ROLL, rc.roll)
            
            # If Hold Turn is on, use the frozen yaw, otherwise use real-time stick
            yaw_val = frozen_yaw if hold_turn else overrides.get(KbAxis.YAW, rc.yaw)

            # --- 2. Handle Mode Switch (Camera modes) ---
            if rc.sw1 != last_camera:
                target = {1: KbButton.CAMERA_WIDE, 0: KbButton.CAMERA_ZOOM, -1: KbButton.CAMERA_IR}.get(rc.sw1)
                if target: k_emu.tap(target)
                last_camera = rc.sw1

            if overrides.get(KbButton.PAUSE, False):
                k_emu.tap(KbButton.PAUSE)

            # --- 3. Handle Buttons (One-shot Taps) ---
            if rc.button2.is_short_tap:
                k_emu.tap(KbButton.ANNOTATION)

            if rc.button3.is_short_tap:
                k_emu.tap(KbButton.PICTURE)

            # --- 4. Handle Keyboard Emulation ---
            # We send the processed pitch_val and yaw_val (either live or frozen)
            k_emu.handle_axis(KbAxis.PITCH, pitch_val)
            k_emu.handle_axis(KbAxis.ROLL, roll_val)
            k_emu.handle_axis(KbAxis.YAW, yaw_val)

            # Extra Camera Yaw (Fast phase) if in Wide mode
            if last_camera == 1:
                k_emu.handle_axis(KbAxis.CAMERA_YAW, yaw_val)

            # Elevation (Throttle)
            k_emu.handle_axis(KbAxis.THROTTLE, rc.throttle)

            # Camera Tilt (Gimbal)
            k_emu.handle_axis(KbAxis.CAMERA_PITCH, rc.tilt) 
            
            time.sleep(0.01) # ~100Hz update rate

    except KeyboardInterrupt:
        print("User interrupted. Closing connection...")
    finally:
        rc.close()
        k_emu.force_cleanup()
        print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DJI RC Interface")
    
    # Define the --model flag
    parser.add_argument(
        '--model', 
        type=str, 
        default='RC3', 
        choices=['RC3', 'N1', 'M300'],
        help='Remote controller model to use (default: RC3)'
    )
    
    args = parser.parse_args()
    
    # Pass the argument value into main
    main(args.model)
