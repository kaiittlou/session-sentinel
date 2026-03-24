import psutil
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, jsonify, request
import threading
import random

from detector import load_data, save_data
from network import get_ip_info
from tokens import find_discord_tokens

try:
    from pync import Notifier
except ImportError:
    Notifier = None

app = Flask(__name__)
data = load_data()

print("Starting Session Sentinel backend...")

DEFAULT_MONITORED_APPS = ["Discord", "Spotify", "Steam", "Firefox"]


def ensure_data_shape():
    global data

    if data is None:
        data = {}

    if data.get("activity") is None:
        data["activity"] = {}

    if data.get("recently_used") is None:
        data["recently_used"] = {}

    if data.get("alerts") is None:
        data["alerts"] = []

    if data.get("timeline") is None:
        data["timeline"] = []

    if data.get("settings") is None:
        data["settings"] = {
            "monitored_apps": DEFAULT_MONITORED_APPS.copy(),
            "dark_mode": False
        }

    if data["settings"].get("monitored_apps") is None:
        data["settings"]["monitored_apps"] = DEFAULT_MONITORED_APPS.copy()

    if data["settings"].get("dark_mode") is None:
        data["settings"]["dark_mode"] = False

    if data.get("risk") is None:
        data["risk"] = {
            "level": "low",
            "score": 0,
            "reasons": []
        }

    if data.get("monitoring") is None:
        data["monitoring"] = {
            "active": True,
            "last_heartbeat": None
        }


ensure_data_shape()


def get_timestamp():
    now = datetime.now(ZoneInfo("Europe/London"))
    return now.isoformat()


def notify(title, message):
    if Notifier:
        try:
            Notifier.notify(message, title=title)
        except Exception:
            pass


def add_timeline_event(app_name, event_type, details=None):
    ensure_data_shape()

    event = {
        "app": app_name,
        "event_type": event_type,
        "details": details or {},
        "time": get_timestamp()
    }

    data["timeline"].append(event)

    if len(data["timeline"]) > 200:
        data["timeline"] = data["timeline"][-200:]


def add_alert(message, severity="medium", app_name=None, details=None):
    ensure_data_shape()

    alert = {
        "message": message,
        "severity": severity,
        "time": get_timestamp(),
        "app": app_name,
        "details": details or {}
    }

    data["alerts"].append(alert)

    if len(data["alerts"]) > 300:
        data["alerts"] = data["alerts"][-300:]

    if severity != "info":
        notify("Session Sentinel", message)


def clear_all_alerts():
    ensure_data_shape()
    data["alerts"] = []


def update_risk_score():
    ensure_data_shape()

    score = 0
    reasons = []

    recent_alerts = data.get("alerts", [])[-10:]

    for alert in recent_alerts:
        severity = alert.get("severity", "medium")

        if severity == "medium":
            score += 15
        elif severity == "high":
            score += 30
        elif severity == "critical":
            score += 50

    if any("token changed" in (a.get("message", "").lower()) for a in recent_alerts):
        reasons.append("Token change detected")

    if any("new country" in (a.get("message", "").lower()) for a in recent_alerts):
        reasons.append("Location anomaly detected")

    if len(recent_alerts) >= 3:
        reasons.append("Multiple recent alerts")

    if score >= 80:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 20:
        level = "medium"
    else:
        level = "low"

    data["risk"] = {
        "level": level,
        "score": min(score, 100),
        "reasons": reasons
    }


def get_monitored_apps():
    ensure_data_shape()
    apps = data.get("settings", {}).get("monitored_apps") or []
    return list(dict.fromkeys(apps))


def get_all_running_process_names():
    names = []

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info["name"]
            if name and name.strip():
                cleaned = name.strip()
                if cleaned not in names:
                    names.append(cleaned)
        except Exception:
            pass

    return sorted(names, key=lambda x: x.lower())


def is_app_running(app_name):
    target = app_name.lower().strip()

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info["name"]
            if not name:
                continue

            if target in name.lower():
                return True
        except Exception:
            pass

    return False


def get_running_apps():
    running = []
    monitored = get_monitored_apps()

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info["name"]
            if not name:
                continue

            lowered = name.lower()

            for app_name in monitored:
                if app_name.lower() in lowered:
                    running.append(app_name)
        except Exception:
            pass

    return list(set(running))


def simulate_attack():
    fake_locations = [
        ("Berlin", "Germany"),
        ("Moscow", "Russia"),
        ("New York", "USA")
    ]

    monitored = get_monitored_apps()
    app_name = random.choice(monitored) if monitored else "Unknown App"
    city, country = random.choice(fake_locations)

    add_alert(
        f"🚨 SIMULATED ATTACK: {app_name} login from {city}, {country}",
        "critical",
        app_name=app_name,
        details={"city": city, "country": country}
    )


def move_app_to_recently_closed(app_name, alert_message=None):
    ensure_data_shape()

    source_info = data["activity"].get(app_name) or data["recently_used"].get(app_name)

    if not source_info:
        ip_data, _ = get_ip_info()
        source_info = {
            "last_active": get_timestamp(),
            "last_seen": time.time(),
            "ip": ip_data.get("ip"),
            "city": ip_data.get("city"),
            "country": ip_data.get("country"),
            "status": "recently closed"
        }

    source_info["status"] = "recently closed"
    source_info["closed_at"] = get_timestamp()
    source_info["last_seen"] = source_info.get("last_seen") or time.time()
    data["recently_used"][app_name] = source_info

    if app_name in data["activity"]:
        del data["activity"][app_name]

    if alert_message:
        add_alert(
            alert_message,
            "info",
            app_name=app_name,
            details={"status": "recently_closed"}
        )


def monitor():
    global data
    known_tokens = set()
    previous_online_state = set()

    while True:
        try:
            ensure_data_shape()

            current_time = time.time()
            apps = get_running_apps()
            ip_data, _ = get_ip_info()

            data["monitoring"]["active"] = True
            data["monitoring"]["last_heartbeat"] = get_timestamp()

            currently_running = set(apps)
            previously_tracked = set((data.get("activity") or {}).keys())

            for app_name in apps:
                previous_info = data["activity"].get(app_name) or data["recently_used"].get(app_name)

                if app_name not in previous_online_state:
                    add_alert(
                        f"{app_name} status changed to online",
                        "info",
                        app_name=app_name,
                        details={"status": "online"}
                    )

                if app_name not in data["activity"]:
                    add_timeline_event(app_name, "opened", {"ip": ip_data.get("ip")})

                if previous_info:
                    old_country = previous_info.get("country")
                    old_city = previous_info.get("city")
                    new_country = ip_data.get("country")
                    new_city = ip_data.get("city")

                    if old_country and new_country and old_country != new_country:
                        add_alert(
                            f"New country detected for {app_name}: {old_country} → {new_country}",
                            "high",
                            app_name=app_name,
                            details={
                                "old_country": old_country,
                                "new_country": new_country,
                                "old_city": old_city,
                                "new_city": new_city,
                                "ip": ip_data.get("ip")
                            }
                        )
                        add_timeline_event(
                            app_name,
                            "location_change",
                            {
                                "old_country": old_country,
                                "new_country": new_country,
                                "old_city": old_city,
                                "new_city": new_city
                            }
                        )

                data["activity"][app_name] = {
                    "last_active": get_timestamp(),
                    "last_seen": current_time,
                    "ip": ip_data.get("ip"),
                    "city": ip_data.get("city"),
                    "country": ip_data.get("country"),
                    "status": "online"
                }

                if app_name in data["recently_used"]:
                    del data["recently_used"][app_name]

            offline_apps = previously_tracked - currently_running

            for app_name in offline_apps:
                last_info = data["activity"].get(app_name)

                if last_info:
                    last_info["status"] = "recently closed"
                    last_info["closed_at"] = get_timestamp()
                    data["recently_used"][app_name] = last_info

                    add_alert(
                        f"{app_name} status changed to offline",
                        "info",
                        app_name=app_name,
                        details={"status": "offline"}
                    )

                    add_timeline_event(
                        app_name,
                        "closed",
                        {
                            "ip": last_info.get("ip"),
                            "city": last_info.get("city"),
                            "country": last_info.get("country")
                        }
                    )

                if app_name in data["activity"]:
                    del data["activity"][app_name]

            previous_online_state = set(currently_running)

            tokens = set(find_discord_tokens())
            if known_tokens and tokens != known_tokens:
                add_alert(
                    "Discord token changed",
                    "critical",
                    app_name="Discord",
                    details={"event": "token_changed"}
                )
                add_timeline_event("Discord", "token_changed", {"event": "token_changed"})

            known_tokens = tokens

            update_risk_score()
            save_data(data)

        except Exception as e:
            print(f"Monitor error: {e}")

        time.sleep(5)


threading.Thread(target=monitor, daemon=True).start()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/data")
def get_data():
    ensure_data_shape()
    return jsonify(data)


@app.route("/simulate")
def simulate():
    simulate_attack()
    save_data(data)
    return {"status": "ok"}


@app.route("/alerts/clear", methods=["POST"])
def clear_alerts():
    clear_all_alerts()
    save_data(data)
    return jsonify({"status": "ok"})


@app.route("/running-apps")
def running_apps():
    return jsonify({"running_apps": get_all_running_process_names()})


@app.route("/settings/apps", methods=["POST"])
def add_monitored_app():
    global data
    ensure_data_shape()

    body = request.get_json(silent=True) or {}
    app_name = (body.get("app_name") or "").strip()

    if not app_name:
        return jsonify({"status": "error", "message": "App name is required"}), 400

    if not is_app_running(app_name):
        return jsonify({"status": "error", "message": "App not found"}), 404

    monitored = data["settings"].get("monitored_apps") or []

    existing_match = None
    for existing in monitored:
        if existing.lower() == app_name.lower():
            existing_match = existing
            break

    if existing_match:
        app_name = existing_match
    else:
        monitored.append(app_name)

    data["settings"]["monitored_apps"] = monitored

    ip_data, _ = get_ip_info()
    current_time = time.time()

    data["activity"][app_name] = {
        "last_active": get_timestamp(),
        "last_seen": current_time,
        "ip": ip_data.get("ip"),
        "city": ip_data.get("city"),
        "country": ip_data.get("country"),
        "status": "online"
    }

    if app_name in data["recently_used"]:
        del data["recently_used"][app_name]

    add_alert(
        f"{app_name} added to current apps",
        "info",
        app_name=app_name,
        details={"action": "added_to_current_apps"}
    )

    add_timeline_event(app_name, "added", {"ip": ip_data.get("ip")})

    save_data(data)

    return jsonify({
        "status": "ok",
        "message": f"{app_name} added to current apps",
        "monitored_apps": monitored
    })


@app.route("/settings/apps/remove", methods=["POST"])
def remove_monitored_app():
    global data
    ensure_data_shape()

    body = request.get_json(silent=True) or {}
    app_name = (body.get("app_name") or "").strip()

    if not app_name:
        return jsonify({"status": "error", "message": "App name is required"}), 400

    monitored = data["settings"].get("monitored_apps") or []

    target_index = None
    matched_name = None

    for i, existing in enumerate(monitored):
        if existing.lower() == app_name.lower():
            target_index = i
            matched_name = existing
            break

    if target_index is None:
        return jsonify({"status": "error", "message": "App not found"}), 404

    monitored.pop(target_index)
    data["settings"]["monitored_apps"] = monitored

    move_app_to_recently_closed(
        matched_name,
        alert_message=f"{matched_name} moved to recently closed apps"
    )

    add_timeline_event(matched_name, "removed", {"action": "moved_to_recently_closed"})

    save_data(data)

    return jsonify({
        "status": "ok",
        "message": f"{matched_name} moved to recently closed apps"
    })


@app.route("/settings/dark-mode", methods=["POST"])
def set_dark_mode():
    ensure_data_shape()

    body = request.get_json(silent=True) or {}
    enabled = bool(body.get("enabled"))

    data["settings"]["dark_mode"] = enabled
    save_data(data)

    return jsonify({"status": "ok", "dark_mode": enabled})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)