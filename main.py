import psutil
import time
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, jsonify
import threading
import random

from detector import load_data, save_data, detect_time_anomaly, detect_impossible_travel
from network import get_ip_info
from tokens import find_discord_tokens
from pync import Notifier  # macOS notifications

TARGET_APPS = ["Discord", "Spotify", "Steam", "Firefox"]

app = Flask(__name__)
data = load_data()

# ---------------- TIME ----------------
def get_timestamp():
    now = datetime.now(ZoneInfo("Europe/London"))
    timezone = now.tzname()
    formatted = now.strftime("%H:%M:%S")
    return f"[{timezone}] {formatted}"

def print_last_active(apps):
    timestamp = get_timestamp()
    app_list = ", ".join(apps) if apps else "None"
    message = f"Last active: {app_list} | {timestamp}"

    sys.stdout.write("\r" + message)
    sys.stdout.flush()

# ---------------- NOTIFICATIONS ----------------
def notify(title, message):
    try:
        Notifier.notify(message, title=title)
    except:
        pass

# ---------------- PROCESS MONITOR ----------------
def get_running_apps():
    running = []
    for process in psutil.process_iter(['name']):
        try:
            name = process.info['name']
            if name:
                for app_name in TARGET_APPS:
                    if app_name.lower() in name.lower():
                        running.append(app_name)
        except:
            pass
    return list(set(running))

# ---------------- ALERT ----------------
def add_alert(type_, message, severity="medium"):
    alert = {
        "type": type_,
        "message": message,
        "severity": severity,
        "time": str(datetime.now())
    }
    data["alerts"].append(alert)
    print("\n⚠️ ALERT:", alert)
    notify("Session Sentinel", message)

# ---------------- SIMULATED ATTACK ----------------
def simulate_attack():
    fake_locations = [
        ("Berlin", "Germany"),
        ("Moscow", "Russia"),
        ("Beijing", "China"),
        ("New York", "USA")
    ]
    app_name = random.choice(TARGET_APPS)
    city, country = random.choice(fake_locations)

    add_alert(
        "security",
        f"🚨 SIMULATED ATTACK: {app_name} login from {city}, {country}",
        "critical"
    )

# ---------------- MONITOR LOOP ----------------
def monitor():
    global data
    last_ip_data = None
    known_tokens = set()

    while True:
        now = datetime.now()
        hour = now.hour
        current_time = time.time()

        apps = get_running_apps()
        print_last_active(apps)

        ip_data, changed = get_ip_info()

        for app_name in apps:
            previous = data["activity"].get(app_name, {})
            data["activity"][app_name] = {
                "last_active": get_timestamp(),
                "last_seen": current_time,
                "hours": previous.get("hours", [])[-20:] + [hour],
                "ip": ip_data.get("ip"),
                "city": ip_data.get("city"),
                "country": ip_data.get("country")
            }

            if detect_time_anomaly(app_name, hour, data):
                add_alert("behavior", f"Unusual {app_name} usage at {hour}:00", "medium")

            if previous.get("ip") and previous.get("ip") != ip_data.get("ip"):
                add_alert(
                    "security",
                    f"{app_name} session IP changed ({previous.get('ip')} → {ip_data.get('ip')})",
                    "critical"
                )

        if changed:
            add_alert("network", f"IP changed to {ip_data['ip']} ({ip_data.get('city')})", "high")

        if last_ip_data and detect_impossible_travel(last_ip_data, ip_data):
            add_alert("network", "Impossible travel detected", "critical")

        last_ip_data = ip_data

        tokens = set(find_discord_tokens())

        if not known_tokens:
            known_tokens = tokens
        elif tokens != known_tokens:
            add_alert("security", "Discord token change detected", "critical")
            known_tokens = tokens

        save_data(data)
        time.sleep(10)

threading.Thread(target=monitor, daemon=True).start()

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/data")
def get_data():
    return jsonify(data)

@app.route("/simulate")
def simulate():
    simulate_attack()
    return {"status": "attack simulated"}

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)