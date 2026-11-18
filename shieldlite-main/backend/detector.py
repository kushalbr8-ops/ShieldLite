import json
import redis
import time
import math
import re

r = redis.Redis(host="localhost", port=6379, db=0)

rules = json.load(open("attack_rules.json"))
behaviour = json.load(open("behaviour_config.json"))

# Additional advanced signatures
ADVANCED_SIGS = {
    "log4shell": ["${jndi:", "${env:", "${sys:"],
    "prototype_pollution": ["__proto__", "constructor.prototype"],
    "shellshock": ["() { :; };"],
    "html_injection": ["<iframe", "<object", "<embed"],
    "template_injection": ["{{", "#{", "${"],
    "scanner_fingerprints": ["sqlmap", "acunetix", "dirbuster", "nmap"],
    "unicode_traversal": ["%uff0e%uff0e", "0x2e", "\u002e"]
}

def shannon_entropy(data):
    if not data:
        return 0
    freq = {}
    for c in data:
        freq[c] = freq.get(c, 0) + 1
    entropy = 0
    length = len(data)
    for f in freq.values():
        p = f / length
        entropy -= p * math.log2(p)
    return entropy

def detect_signature(payload: str):
    if not payload:
        return None

    text = payload.lower()

    # Basic signatures
    for attack_type, patterns in rules.items():
        for p in patterns:
            if p.lower() in text:
                return attack_type

    # Advanced signatures
    for attack_type, patterns in ADVANCED_SIGS.items():
        for p in patterns:
            if p.lower() in text:
                return attack_type

    return None

def detect_anomaly(ip: str, payload: str, endpoint: str):
    score = 0
    reasons = []

    # Entropy
    ent = shannon_entropy(payload)
    if ent > 4.5:
        score += 2
        reasons.append("high_entropy")

    # Repeated payload pattern
    key = f"payload:{ip}:{payload[:20]}"
    count = r.incr(key)
    r.expire(key, 120)
    if count > 10:
        score += 2
        reasons.append("repeated_payload")

    # Rare endpoint detection
    ep_key = f"endpoint_global:{endpoint}"
    ep_count = r.incr(ep_key)
    r.expire(ep_key, 86400)
    if ep_count < 3:
        score += 1
        reasons.append("rare_endpoint")

    # User-agent anomaly
    # we handle in main (extract UA from request headers) — but you can add here if needed

    # Unicode anomaly
    if re.search(r"\\u[0-9a-f]{4}", payload.lower()):
        score += 2
        reasons.append("unicode_anomaly")

    # Honeypot endpoint
    if endpoint.startswith("/__debug__"):
        score += 5
        reasons.append("honeypot_triggered")

    if score >= 8:
        return "zero_day_like", reasons
    if score >= 6:
        return "high_risk", reasons
    if score >= 4:
        return "medium_risk", reasons

    return None, reasons

def detect_behaviour(ip: str, endpoint: str):
    # Rate limiting
    key = f"rate:{ip}"
    request_count = r.incr(key)
    r.expire(key, 60)

    if request_count > behaviour["max_requests_per_minute"]:
        return "api_abuse / rate_limit"

    # Sensitive endpoints
    for se in behaviour["suspicious_endpoints"]:
        if se in endpoint:
            atk = r.incr(f"endpoint:{ip}:{se}")
            r.expire(f"endpoint:{ip}:{se}", 60)

            if atk > 3:
                return "endpoint_scanning"

    return None