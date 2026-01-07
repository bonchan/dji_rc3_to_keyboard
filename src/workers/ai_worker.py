from src.utils.logger_setup import setup_logger
import time
import queue
import threading
import uuid
import mss
import cv2
import json
import numpy as np
import requests
from ultralytics import YOLO

from src.api.fh_client import FlightHubClient
from src.utils.fh_mapper import map_topologies

from src.utils.config_manager import load_config

# --- FLIGHTHUB CONFIG ---
FH_HOST = 'https://es-flight-api-us.djigate.com'

class AIWorker:
    def __init__(self, trigger_queue, status_queue, shared_config, session_timestamp):
        self.logger = setup_logger("AI_WORKER", session_timestamp)
        self.trigger_queue = trigger_queue
        self.status_queue = status_queue  # Use this for heartbeats
        self.shared_config = shared_config # Use this for settings

        # Initial API setup
        self.fh_client = FlightHubClient(
            org_key=self.shared_config.get("organization_key"), 
            base_url=FH_HOST
        )

        self.running = True
        self.model = None
        self.sct = None

    def setup(self):
        """Initialize heavy resources once"""
        self.logger.info("🤖 AI: Loading YOLOv11 and MSS Screen Capture...")
        # Load model from the path in your project
        self.model = YOLO('models/insulator_pr15.pt')
        self.sct = mss.mss()
        # Monitor 1 is usually the primary display where the drone stream is
        self.monitor = self.sct.monitors[2]

    def telemetry_task(self, req_id, drone_sn, project_uuid):
        """Background thread for DJI API"""
        try:
            st = time.time()
            # We pass these in as arguments so they don't change mid-request
            data = self.fh_client.get_projects_topologies(project_uuid)
            et = time.time()
            
            self.logger.info(f'📡 API request took {(et - st) * 1000:.2f} ms')
            
            drone_data = map_topologies(data, drone_sn)
            self.logger.info(f"📍 Mapped Telemetry: {json.dumps(drone_data, indent=4)}")
            self.logger.info(f"✅ Telemetry sync complete for {req_id[:8]}")
        except Exception as e:
            self.logger.error(f"⚠️ Telemetry failed for {req_id[:8]}: {e}")

    def execute_detection(self):
        """Fast capture + AI Inference"""
        # GRAB LIVE VALUES FROM SHARED CONFIG
        drone_sn = self.shared_config.get("drone_sn")
        project_uuid = self.shared_config.get("project_uuid")
        confidence = self.shared_config.get("ai_confidence", 0.5)
        use_left = self.shared_config.get("screen_left", True)
        use_right = self.shared_config.get("screen_right", True)
        
        # FIXME
        req_id = str(uuid.uuid4())
        
        # 1. Capture Screen
        sct_img = self.sct.grab(self.monitor)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        height, width, _ = img.shape
        mid = width // 2

        if use_left and not use_right:
            img = img[:, :mid] # Keep only left half
            self.logger.info("✂️ AI: Processing LEFT half only.")
        elif use_right and not use_left:
            img = img[:, mid:] # Keep only right half
            self.logger.info("✂️ AI: Processing RIGHT half only.")

        self.logger.info(f"🎯 Action: Detect triggered for {drone_sn}")

        # 2. Fire telemetry (passing live values)
        threading.Thread(
            target=self.telemetry_task, # Renamed to logic for clarity
            args=(req_id, drone_sn, project_uuid), 
            daemon=True
        ).start()

        # 3. YOLO Inference
        results = self.model.predict(img, conf=confidence, verbose=False)
        count = len(results[0].boxes)
        self.logger.info(f"✅ AI Done [{req_id[:8]}]: Found {count} objects.")


        annotated_frame = results[0].plot()
        success, buffer = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if success:
            # Send to GUI via the status_queue
            self.status_queue.put({
                "status_update": "DETECTION_SNAPSHOT", 
                "image": buffer.tobytes(),
                "count": count
            })


    def run(self):
        # Initial Heartbeat
        self.status_queue.put({"status_update": "AI", "state": "offline"})
        last_heartbeat = time.time()

        self.setup()
        while self.running:

            current_org = self.shared_config.get("organization_key")
            if current_org != self.fh_client.org_key:
                self.logger.info("🔄 AI: Org Key changed. Re-initializing FlightHub Client...")
                self.fh_client = FlightHubClient(org_key=current_org, base_url=FH_HOST)


            # Send heartbeat every 5 seconds to keep the GUI light green
            if time.time() - last_heartbeat > 5:
                self.status_queue.put({"status_update": "AI", "state": "running"})
                last_heartbeat = time.time()

            try:
                # Listen for Triggers (RC -> AI)
                msg = self.trigger_queue.get(timeout=0.1)
                
                # Check if detection is enabled in GUI before processing
                if self.shared_config.get("trigger_detection", True):
                    self.execute_detection()
                else:
                    self.logger.info("🚫 AI: Trigger received but Detection is DISABLED in UI.")

            except queue.Empty:
                pass

# --- THE BOOTSTRAP ---
def run_ai_worker(trigger_queue, status_queue, shared_config, session_timestamp):
    worker = AIWorker(trigger_queue, status_queue, shared_config, session_timestamp)
    worker.run()