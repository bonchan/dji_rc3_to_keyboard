from src.utils.logger_setup import setup_logger
import time
from src.remote_controller.dji_rc3 import DJIRC3
from src.remote_controller.dji_rcN1 import DJIRCN1
from src.remote_controller.dji_m300 import DJIM300
from src.remote_controller.base_rc import RCConnectionError

from src.utils.sequence import SequenceHandler, SequenceStep
from src.keyboard.keyboard import KeyboardEmulator, KbAxis, KbButton

from src.utils.config_manager import load_config

CROSS_AND_TURN = [
        SequenceStep(duration=3.0, axes_map={KbAxis.PITCH: 1.0, KbAxis.YAW: 0.0}), # Cross
        SequenceStep(duration=0.1, axes_map={KbButton.PAUSE: True}), # Wait
        SequenceStep(duration=8.0, axes_map={KbAxis.PITCH: 0.0, KbAxis.YAW: 1.0}), # Turn 180
    ]

# src/workers/rc_worker.py
class RCWorker:
    def __init__(self, trigger_queue, status_queue, shared_config, session_timestamp):
        self.logger = setup_logger("RC_WORKER", session_timestamp)
        self.trigger_queue = trigger_queue
        self.status_queue = status_queue  # New
        self.shared_config = shared_config  # New: replacing local config load
        
        # Read initial values from shared memory
        self.model_choice = self.shared_config.get("model_choice", "RC3")
        
        self.rc = None
        self.running = True
        # State variables
        

        self.k_emu = KeyboardEmulator(emulate_hardware=True, print_events=True)
        self.seq_handler = SequenceHandler()

        self.last_camera = None
        self.hold_cruise = False
        self.hold_turn = False
        self.seq_running = False

        self.frozen_pitch = 0.0
        self.frozen_roll = 0.0
        self.frozen_yaw = 0.0



    def setup(self):
        self.logger.info(f"🕹️ RC: Connecting to {self.model_choice}...")
        retry_limit = 15

        for retry in range(retry_limit):
            try:
                if self.model_choice == 'RC3':
                    self.rc = DJIRC3(joystick_index=0, deadzone_threshold_movement=0.3, deadzone_threshold_elevation=0.6)
                elif self.model_choice == 'M300':
                    self.rc = DJIM300()
                elif self.model_choice == 'N1':
                    self.rc = DJIRCN1()
                
                # If we reach this line, constructor succeeded
                self.logger.info(f"Successfully connected to {self.model_choice}!")
                break 
                
            except RCConnectionError as e:
                self.rc = None
                self.logger.info(f"Retrying... [{retry}/{retry_limit}] {e}")
                time.sleep(1)

    def run(self):
        # Initial Heartbeat
        self.status_queue.put({"status_update": "RC", "state": "offline"})
        self.setup()
        try:
            self.logger.info("Streaming data. Press Ctrl+C to stop.")
            while self.running:
                if not self.rc.is_connected:
                    self.logger.info("[!!!] CONTROLLER DISCONNECTED [!!!]")
                    break

                if not self.rc.update(): continue

                new_model = self.shared_config.get("model_choice")
                if new_model != self.model_choice:
                    self.logger.info(f"🔄 GUI changed model to {new_model}. Reconnecting...")
                    if self.rc: self.rc.close()
                    self.model_choice = new_model
                    self.setup()
                    continue

                if time.time() % 2 < 0.02: # Simple pulse check
                    self.status_queue.put({"status_update": "RC", "state": "running"})

                if self.rc.button1.is_short_tap:
                    self.logger.info('>>> Emergency PAUSE for 3 sec <<<')
                    self.seq_handler.stop()
                    self.k_emu.force_cleanup()
                    self.hold_cruise = False
                    self.hold_turn = False
                    time.sleep(3)
                    self.logger.info('>>> Emergency PAUSE Finished <<<')
                    continue

                if self.rc.button3.is_long_press and not (self.hold_cruise or self.hold_turn):
                    if self.seq_running:
                        self.seq_handler.stop()
                    else:
                        self.seq_handler.start_sequence(CROSS_AND_TURN)

                overrides, self.seq_running = self.seq_handler.update()
                
                if not self.seq_running:
                    # --- enable cruise ---
                    if self.rc.button4.is_short_tap:
                        if self.hold_cruise:
                            self.logger.info('>>> DISABLE CRUISE <<<')
                            self.hold_cruise = False
                        else:
                            if self.hold_turn:
                                self.logger.info('>>> DISABLE TURN <<<')
                                self.hold_turn = False
                            elif self.rc.yaw != 0:
                                self.logger.info('>>> ENABLE TURN <<<')
                                self.frozen_yaw = self.rc.yaw
                                self.hold_turn = True

                    if self.rc.button1.is_maintained_long_press and self.rc.button4.is_short_tap:
                        self.logger.info('>>> ENABLE FORWARD CRUISE <<<')
                        self.hold_cruise = True
                        self.frozen_pitch = 1
                        self.frozen_roll = 0

                    if self.rc.button4.is_long_press:
                        if self.rc.pitch != 0 or self.rc.roll != 0:
                            self.logger.info('>>> ENABLE FREE CRUISE <<<')
                            self.hold_cruise = True
                            self.frozen_pitch = self.rc.pitch
                            self.frozen_roll = self.rc.roll
                        else:
                            self.logger.info('>>> FREE CRUISE HAS NO VALUES TO CRUISE<<<')

                

                # --- Determine Final Axis Values ---
                # If Cruise is on, use the frozen pitch, otherwise use real-time stick
                pitch_val = self.frozen_pitch if self.hold_cruise else overrides.get(KbAxis.PITCH, self.rc.pitch)
                
                # Roll remains real-time unless you want to lock that too
                roll_val = self.frozen_roll if self.hold_cruise else overrides.get(KbAxis.ROLL, self.rc.roll)
                
                # If Hold Turn is on, use the frozen yaw, otherwise use real-time stick
                yaw_val = self.frozen_yaw if self.hold_turn else overrides.get(KbAxis.YAW, self.rc.yaw)

                # --- 2. Handle Mode Switch (Camera modes) ---
                if self.rc.sw1 != self.last_camera:
                    target = {1: KbButton.CAMERA_WIDE, 0: KbButton.CAMERA_ZOOM, -1: KbButton.CAMERA_IR}.get(self.rc.sw1)
                    if target: self.k_emu.tap(target)
                    self.last_camera = self.rc.sw1

                if overrides.get(KbButton.PAUSE, False):
                    self.k_emu.tap(KbButton.PAUSE)

                # --- 3. Handle Buttons (One-shot Taps) ---
                if self.rc.button2.is_short_tap:
                    self.k_emu.tap(KbButton.ANNOTATION)

                if self.rc.button3.is_short_tap:
                    # Read boolean directly from shared memory
                    if self.shared_config.get("trigger_detection", True):
                        self.logger.info('🎯 RC: Triggering AI...')
                        self.trigger_queue.put("detect")
                    else:
                        self.logger.info('🚫 RC: Trigger ignored (Detection disabled in GUI)')
                        
                    self.k_emu.tap(KbButton.PICTURE)

                # --- 4. Handle Keyboard Emulation ---
                # We send the processed pitch_val and yaw_val (either live or frozen)
                self.k_emu.handle_axis(KbAxis.PITCH, pitch_val)
                self.k_emu.handle_axis(KbAxis.ROLL, roll_val)
                self.k_emu.handle_axis(KbAxis.YAW, yaw_val)

                # Extra Camera Yaw (Fast phase) if in Wide mode
                if self.last_camera == 1:
                    self.k_emu.handle_axis(KbAxis.CAMERA_YAW, yaw_val)

                # Elevation (Throttle)
                self.k_emu.handle_axis(KbAxis.THROTTLE, self.rc.throttle)

                # Camera Tilt (Gimbal)
                self.k_emu.handle_axis(KbAxis.CAMERA_PITCH, self.rc.tilt) 
                
                time.sleep(0.01) # ~100Hz update rate

        except KeyboardInterrupt:
            self.logger.info("User interrupted. Closing connection...")
        finally:
            self.status_queue.put({"status_update": "RC", "state": "offline"})
            if self.rc:
                self.rc.close()
            self.k_emu.force_cleanup()
            self.logger.info("Done.")

def run_rc_worker(trigger_queue, status_queue, shared_config, session_timestamp):
    worker = RCWorker(trigger_queue, status_queue, shared_config, session_timestamp)
    worker.run()