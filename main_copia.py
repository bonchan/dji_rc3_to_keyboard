import time
import argparse
import serial.tools.list_ports
from src.remote_controller.dji_rc3_copia import DJIRC3
from src.remote_controller.dji_rcN1 import DJIRCN1
from src.remote_controller.dji_m300 import DJIM300
from src.remote_controller.base_rc import RCConnectionError

from src.utils.sequence import SequenceHandler, SequenceStep
from src.keyboard.keyboard import KeyboardEmulator, KbAxis, KbButton

from src.mouse.mouse import MouseEmulator 

def main(model_choice):
    print(f"--- DJI Universal Interface | Target: {model_choice} ---")

    rc = None
    retry_limit = 15

    for retry in range(retry_limit):
        try:
            if model_choice == 'RC3':
                # El RC3 ahora recibe los umbrales de zona muerta correctamente
                rc = DJIRC3(joystick_index=0, deadzone_threshold_movement=0.3, deadzone_threshold_elevation=0.02)
            elif model_choice == 'M300':
                rc = DJIM300()
            elif model_choice == 'N1':
                rc = DJIRCN1()
            
            print(f"Successfully connected to {model_choice}!")
            break 
            
        except RCConnectionError as e:
            rc = None
            print(f"Retrying... [{retry}/{retry_limit}] {e}")
            time.sleep(1)

    if not rc:
        print("Could not connect to any controller. Exiting.")
        return

    k_emu = KeyboardEmulator(emulate_hardware=True, print_events=True)
    m_emu = MouseEmulator(emulate_hardware=True, print_events=True)

    seq_handler = SequenceHandler()
    cross_and_turn = [
        SequenceStep(duration=3.0, axes_map={KbAxis.PITCH: 1.0, KbAxis.YAW: 0.0}),
        SequenceStep(duration=0.1, axes_map={KbButton.PAUSE: True}),
        SequenceStep(duration=8.0, axes_map={KbAxis.PITCH: 0.0, KbAxis.YAW: 1.0}),
    ]

    last_camera = None
    hold_cruise = False
    hold_turn = False
    seq_running = False

    frozen_pitch = 0.0
    frozen_roll = 0.0
    frozen_yaw = 0.0

    try:
        print("Streaming data. Press Ctrl+C to stop.")
        while True:
            if not rc.is_connected:
                print("[!!!] CONTROLLER DISCONNECTED [!!!]")
                break

            if not rc.update(): continue

            # --- Manejo de Emergencia ---
            if rc.button1.is_short_tap:
                print('>>> Emergency PAUSE for 3 sec <<<')
                seq_handler.stop()
                k_emu.force_cleanup()
                m_emu.cleanup() 
                hold_cruise = False
                hold_turn = False
                time.sleep(3)
                continue

            # --- Manejo de Secuencias ---
            if rc.button3.is_long_press and not (hold_cruise or hold_turn):
                if seq_running:
                    seq_handler.stop()
                else:
                    seq_handler.start_sequence(cross_and_turn)

            overrides, seq_running = seq_handler.update()
            
            # --- Lógica de Cruise/Turn ---
            if not seq_running:
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

            # --- Determine Final Axis Values ---
            pitch_val = frozen_pitch if hold_cruise else overrides.get(KbAxis.PITCH, rc.pitch)
            roll_val = frozen_roll if hold_cruise else overrides.get(KbAxis.ROLL, rc.roll)
            yaw_val = frozen_yaw if hold_turn else overrides.get(KbAxis.YAW, rc.yaw)

            # --- 2. Handle Mode Switch (Camera modes) ---
            if rc.sw1 != last_camera:
                target = {1: KbButton.CAMERA_WIDE, 0: KbButton.CAMERA_ZOOM, -1: KbButton.CAMERA_IR}.get(rc.sw1)
                if target: k_emu.tap(target)
                last_camera = rc.sw1

            if overrides.get(KbButton.PAUSE, False):
                k_emu.tap(KbButton.PAUSE)

            # --- 3. Handle Buttons ---
            if rc.button2.is_short_tap:
                k_emu.tap(KbButton.ANNOTATION)

            if rc.button3.is_short_tap:
                k_emu.tap(KbButton.PICTURE)

            # --- 4. Handle Keyboard Emulation ---
            k_emu.handle_axis(KbAxis.PITCH, pitch_val)
            k_emu.handle_axis(KbAxis.ROLL, roll_val)
            k_emu.handle_axis(KbAxis.YAW, yaw_val)

            if last_camera == 1:
                k_emu.handle_axis(KbAxis.CAMERA_YAW, yaw_val)

            k_emu.handle_axis(KbAxis.THROTTLE, rc.throttle)
            k_emu.handle_axis(KbAxis.CAMERA_PITCH, rc.tilt) 

            # --- 5. Handle Mouse ZOOM (Proporcional) ---
            if rc.zoom != 0:
                # rc.zoom es un valor entre -1.0 y 1.0
                # Sensibilidad: ajusta este multiplicador (ej. 5.0 o 10.0) 
                # para que el zoom sea más rápido o lento.
                sensibilidad = 0.2 
                
                # NO usamos int() todavía para no perder la precisión decimal
                # pynput acepta valores flotantes para scroll suave en algunos sistemas
                m_emu.ZOOM(rc.zoom * sensibilidad)
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("User interrupted. Closing connection...")
    finally:
        if rc: rc.close()
        k_emu.force_cleanup()
        m_emu.force_cleanup() 
        print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DJI RC Interface")
    parser.add_argument('--model', type=str, default='RC3', choices=['RC3', 'N1', 'M300'])
    args = parser.parse_args()
    main(args.model)