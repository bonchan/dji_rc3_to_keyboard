import time

class SequenceStep:
    def __init__(self, duration, axes_map):
        """
        duration: Seconds to run this step
        axes_map: Dict, e.g., {KbAxis.PITCH: 0.5, KbAxis.YAW: 0.2}
        """
        self.duration = duration
        self.axes_map = axes_map

class SequenceHandler:
    def __init__(self):
        self.steps = []
        self.active = False
        self.current_step_idx = 0
        self.step_start_time = 0

    def start_sequence(self, steps_list):
        if not steps_list:
            return
        self.steps = steps_list
        self.current_step_idx = 0
        self.step_start_time = time.time()
        self.active = True
        print(f">>> SEQUENCE STARTED: {len(self.steps)} steps loaded.")

    def stop(self):
        if self.active:
            print(">>> SEQUENCE TERMINATED <<<")
        self.active = False
        self.steps = []

    def update(self):
        """
        Returns: (axes_to_override_dict, is_running)
        """
        # 1. Check if we are active and within bounds
        if not self.active or self.current_step_idx >= len(self.steps):
            if self.active: # If we were active but just hit the end
                print(">>> SEQUENCE FINISHED <<<")
                self.active = False
            return {}, False

        current_step = self.steps[self.current_step_idx]
        elapsed = time.time() - self.step_start_time

        # 2. Check if current step is finished
        if elapsed >= current_step.duration:
            self.current_step_idx += 1
            self.step_start_time = time.time()
            
            # Check if there's actually another step coming
            if self.current_step_idx < len(self.steps):
                print(f">>> STEP {self.current_step_idx + 1}/{len(self.steps)}")
                # Recurse to immediately start the next step's logic
                return self.update()
            else:
                print(">>> SEQUENCE FINISHED <<<")
                self.active = False
                return {}, False

        return current_step.axes_map, True