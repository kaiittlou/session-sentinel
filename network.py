import requests

def get_ip_info():
    try:
        res = requests.get("http://ip-api.com/json/", timeout=3)
        data = res.json()
        return {
            "ip": data.get("query"),
            "country": data.get("country"),
            "city": data.get("city")
        }, False
    except:
        return {
            "ip": "unknown",
            "country": "unknown",
            "city": "unknown"
        }, False