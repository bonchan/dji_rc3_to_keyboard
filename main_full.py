import multiprocessing as mp
import sys
import time
from datetime import datetime
from src.workers.rc_worker import run_rc_worker
from src.workers.ai_worker import run_ai_worker
from src.workers.gui_worker import run_gui_worker
from src.utils.config_manager import load_config

def start_worker(name, target, args):
    p = mp.Process(target=target, args=args, name=name)
    p.start()
    print(f"✅ Started {name} (PID: {p.pid})")
    return p

if __name__ == "__main__":
    # 1. Communication Channels
    trigger_queue = mp.Queue()  # RC -> AI (Fast Trigger)
    status_queue = mp.Queue()   # RC/AI -> GUI (Uplink/Heartbeats)
    
    # 2. Shared Live Configuration
    manager = mp.Manager()
    shared_config = manager.dict()
    
    # Load initial data from root/config.json into memory
    initial_data = load_config()
    for key, value in initial_data.items():
        shared_config[key] = value

    # 3. Session Identification (For Logger)
    session_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 4. Define Worker Specifications
    # Note: Everyone gets 'shared_config' for live strings/bools
    worker_specs = {
        "RC_Worker": {
            "target": run_rc_worker,
            "args": (trigger_queue, status_queue, shared_config, session_timestamp)
        },
        "AI_Worker": {
            "target": run_ai_worker,
            "args": (trigger_queue, status_queue, shared_config, session_timestamp)
        },
        "GUI_Worker": {
            "target": run_gui_worker,
            "args": (status_queue, shared_config, session_timestamp)
        }
    }

    processes = {}

    print("🚀 Starting Supervised Drone Satellite System...")
    print(f"📅 Session: {session_timestamp}")
    print("-----------------------------------")

    # Initial start
    for name, spec in worker_specs.items():
        processes[name] = start_worker(name, spec["target"], spec["args"])

    try:
        while True:
            time.sleep(2)  # Watchdog frequency
            
            # Check GUI first - if user closed the window, we exit
            if not processes["GUI_Worker"].is_alive():
                print("🏁 GUI closed by user. Initiating full shutdown...")
                break

            # Check other workers
            for name in ["RC_Worker", "AI_Worker"]:
                if not processes[name].is_alive():
                    print(f"⚠️ ALERT: {name} died! Exit code: {processes[name].exitcode}. Restarting...")
                    spec = worker_specs[name]
                    processes[name] = start_worker(name, spec["target"], spec["args"])

    except KeyboardInterrupt:
        print("\n🛑 Shutdown signal received via Terminal...")
    
    finally:
        print("Cleaning up processes...")
        for name, p in processes.items():
            if p.is_alive():
                p.terminate()
                p.join()
        
        print("✅ System offline.")
        sys.exit(0)