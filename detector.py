import json
import os
import math

LOG_FILE = "data.json"

def default_data():
    return {
        "activity": {},
        "alerts": [],
        "ip_history": []
    }

def load_data():
    data = default_data()
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                loaded = json.load(f)
                data.update(loaded)
        except:
            print("Corrupted data.json — resetting")
    return data

def save_data(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def detect_time_anomaly(app, hour, data):
    if app not in data["activity"]:
        return False
    hours = data["activity"][app].get("hours", [])
    if len(hours) < 5:
        return False
    avg = sum(hours) / len(hours)
    return abs(hour - avg) > 6

def detect_impossible_travel(old, new):
    try:
        if not old or not new:
            return False
        if "lat" not in old or "lat" not in new:
            return False
        if old["lat"] is None or new["lat"] is None:
            return False
        distance = math.sqrt(
            (old["lat"] - new["lat"])**2 +
            (old["lon"] - new["lon"])**2
        )
        return distance > 20
    except:
        return False