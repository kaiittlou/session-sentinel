import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "data.json")

def default_data():
    return {
        "activity": {},
        "recently_used": {},
        "alerts": [],
        "timeline": [],
        "settings": {
            "monitored_apps": ["Discord", "Spotify", "Steam", "Firefox"],
            "dark_mode": False
        },
        "risk": {
            "level": "low",
            "score": 0,
            "reasons": []
        },
        "monitoring": {
            "active": True,
            "last_heartbeat": None
        }
    }

def load_data():
    data = default_data()

    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                loaded = json.load(f)

            data["activity"] = loaded.get("activity") or {}
            data["recently_used"] = loaded.get("recently_used") or {}
            data["alerts"] = loaded.get("alerts") or []
            data["timeline"] = loaded.get("timeline") or []

            loaded_settings = loaded.get("settings") or {}
            data["settings"]["monitored_apps"] = loaded_settings.get("monitored_apps") or ["Discord", "Spotify", "Steam", "Firefox"]
            data["settings"]["dark_mode"] = loaded_settings.get("dark_mode", False)

            loaded_risk = loaded.get("risk") or {}
            data["risk"]["level"] = loaded_risk.get("level", "low")
            data["risk"]["score"] = loaded_risk.get("score", 0)
            data["risk"]["reasons"] = loaded_risk.get("reasons") or []

            loaded_monitoring = loaded.get("monitoring") or {}
            data["monitoring"]["active"] = loaded_monitoring.get("active", True)
            data["monitoring"]["last_heartbeat"] = loaded_monitoring.get("last_heartbeat")
            
        except:
            return default_data()

    return data

def save_data(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)