#!/usr/bin/env python3
# agent/syslog-listener.py
# Usage: python3 syslog-listener.py --bind 0.0.0.0 --port 5514 --backend http://127.0.0.1:8000/event --api-key yourkey

import socket
import argparse
import requests
import re
import threading
from queue import Queue

NGINX_REGEX = re.compile(r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}) - (?P<user>[^ ]+) \[(?P<time>[^\]]+)\] "(?P<method>[A-Z]+) (?P<uri>[^ ]+) (?P<proto>[^"]+)" (?P<status>\d{3}) (?P<size>\d+) "(?P<referer>[^"]*)" "(?P<ua>[^"]*)"')

def worker(q, backend, api_key, timeout=5):
    headers = {"Content-Type":"application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key
    while True:
        data = q.get()
        if data is None:
            break
        try:
            resp = requests.post(backend, json=data, headers=headers, timeout=timeout)
            # optional: log failures
            if resp.status_code != 200:
                print(f"[WARN] backend returned {resp.status_code} for ip {data.get('ip')} resp={resp.text}")
        except Exception as e:
            print(f"[ERROR] failed to post to backend: {e}")
        q.task_done()

def parse_nginx_line(line):
    m = NGINX_REGEX.search(line)
    if not m:
        return None
    d = m.groupdict()
    payload = {
        "ip": d.get("ip"),
        "payload": f'{d.get("method")} {d.get("uri")} status={d.get("status")} ua="{d.get("ua")}"',
        "endpoint": d.get("uri")
    }
    return payload

def main(bind, port, backend, api_key, workers):
    q = Queue()
    for _ in range(workers):
        t = threading.Thread(target=worker, args=(q, backend, api_key), daemon=True)
        t.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind, port))
    print(f"[+] Syslog UDP listener started on {bind}:{port} -> forwarding to {backend}")

    try:
        while True:
            data, addr = sock.recvfrom(65535)
            try:
                line = data.decode(errors='ignore').strip()
            except:
                continue
            parsed = parse_nginx_line(line)
            if parsed:
                q.put(parsed)
            else:
                # fallback: try to extract first IP and send whole message
                ip_match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', line)
                payload = {
                    "ip": ip_match.group(1) if ip_match else addr[0],
                    "payload": line,
                    "endpoint": "/syslog"
                }
                q.put(payload)
    except KeyboardInterrupt:
        print("Stopping listener...")
        q.put(None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5514)
    parser.add_argument("--backend", required=True, help="Backend /event URL")
    parser.add_argument("--api-key", default="", help="SHIELD API KEY used for header")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    main(args.bind, args.port, args.backend, args.api_key, args.workers)