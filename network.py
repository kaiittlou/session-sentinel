import requests

last_ip = None

def get_ip_info():
    global last_ip
    try:
        res = requests.get("http://ip-api.com/json/")
        data = res.json()
        ip_data = {
            "ip": data.get("query"),
            "country": data.get("country"),
            "city": data.get("city"),
            "lat": data.get("lat"),
            "lon": data.get("lon")
        }
        changed = last_ip and last_ip != ip_data["ip"]
        last_ip = ip_data["ip"]
        return ip_data, changed
    except:
        return {
            "ip": "unknown",
            "country": "unknown",
            "city": "unknown",
            "lat": None,
            "lon": None
        }, False