# backend/ip_blocker.py
import os
import redis
import time
import requests

r = redis.Redis(host="localhost", port=6379, db=0)

CF_TOKEN = os.getenv("CLOUDFLARE_TOKEN", "")
ZONE_ID = os.getenv("CF_ZONE_ID", "")

class LocalBlock:
    key_prefix = "shield:block:"

    def block(self, ip, ttl=3600):
        r.setex(self.key_prefix + ip, ttl, "1")

    def is_blocked(self, ip):
        return r.exists(self.key_prefix + ip) == 1

    def unblock(self, ip):
        return r.delete(self.key_prefix + ip)

    def list(self):
        keys = r.keys(self.key_prefix + "*")
        return [k.decode().replace(self.key_prefix, "") for k in keys]

local_block = LocalBlock()

def _has_cf():
    return bool(CF_TOKEN and ZONE_ID)

def block_ip(ip: str, reason: str):
    """
    Try to block via Cloudflare if configured; otherwise do a local Redis block.
    Returns True if blocked locally or via Cloudflare.
    """
    if _has_cf():
        try:
            cf = requests
            url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/firewall/access_rules/rules"
            headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
            data = {
                "mode": "block",
                "configuration": {"target": "ip", "value": ip},
                "notes": f"ShieldLite Automatic Block: {reason}"
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            resp.raise_for_status()
            print(f"[CF] Blocked {ip}: {resp.status_code}")
            return True
        except Exception as e:
            print(f"[CF ERROR] Could not block via Cloudflare: {e}. Falling back to local block.")
    # fallback local block
    local_block.block(ip, ttl=24*3600)
    print(f"[LOCAL] Blocked {ip} locally.")
    return True

def unblock_ip(ip: str):
    """
    Unblock an IP either from Cloudflare (if configured) or from local Redis.
    Returns a dict with result info: {"cloudflare": bool, "local": bool, "deleted_cf_rule_id": str|None}
    """
    result = {"cloudflare": False, "local": False, "deleted_cf_rule_id": None, "errors": []}

    # First: try Cloudflare (if available) — find rules matching this IP and delete them
    if _has_cf():
        try:
            headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
            # list rules (fetch pages of 50; small zones will be fine)
            url_list = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/firewall/access_rules/rules"
            params = {"per_page": 50}
            resp = requests.get(url_list, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            j = resp.json()
            found_ids = []
            for r_item in j.get("result", []):
                cfg = r_item.get("configuration", {})
                if cfg.get("target") == "ip" and cfg.get("value") == ip:
                    found_ids.append(r_item.get("id"))
            # delete found rule(s)
            for rid in found_ids:
                del_url = f"{url_list}/{rid}"
                dresp = requests.delete(del_url, headers=headers, timeout=10)
                dresp.raise_for_status()
                result["cloudflare"] = True
                result["deleted_cf_rule_id"] = rid
            # if none found, still mark as not-found (but not an error)
        except Exception as e:
            result["errors"].append(f"cloudflare_error:{e}")
            print(f"[CF ERROR] Could not list/delete rule for {ip}: {e}")

    # Always attempt local unblock
    try:
        removed = local_block.unblock(ip)
        if removed:
            result["local"] = True
    except Exception as e:
        result["errors"].append(f"local_unblock_error:{e}")
        print(f"[LOCAL ERROR] Could not remove local block for {ip}: {e}")

    return result

def list_local_blocks():
    return local_block.list()