import json
import os

# This gets the absolute path to the directory containing main.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(BASE_DIR, "config","config.json")

DEFAULT_CONFIG = {
    "drone_sn": "",
    "project_uuid": "",
    "organization_key": "",
    "model_choice": "RC3",
    "trigger_detection": True,
    "ai_confidence": 0.5,
    "screen_left": True,
    "screen_right": True,
}

def load_config():
    try:
        if not os.path.exists(CONFIG_FILE):
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config_dict):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=4)
    except Exception as e:
        print(f"⚠️ Error saving config: {e}")