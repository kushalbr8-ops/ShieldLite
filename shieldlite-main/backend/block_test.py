# backend/block_test.py
import requests, os
API_URL = "http://127.0.0.1:8000/event"
KEY = os.getenv("SHIELD_API_KEY", "")

def send_event(ip, payload, endpoint="/test"):
    headers = {"Content-Type":"application/json"}
    if KEY:
        headers["X-API-KEY"] = KEY
    data = {"ip": ip, "payload": payload, "endpoint": endpoint}
    r = requests.post(API_URL, json=data, headers=headers)
    print(r.status_code, r.text)

if __name__ == "__main__":
    send_event("1.2.3.4", "UNION SELECT * FROM users", "/login")