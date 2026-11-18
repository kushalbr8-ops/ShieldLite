# backend/main.py
from fastapi import FastAPI, Request, HTTPException, Header
from detector import detect_signature, detect_behaviour, detect_anomaly
from ip_blocker import block_ip, local_block, unblock_ip, list_local_blocks
from db import log_attack
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

app = FastAPI()

SHIELD_API_KEY = os.getenv("SHIELD_API_KEY", "")

# helper: extract client ip
def get_client_ip(request: Request, body_ip=None):
    # priority: explicit body ip -> X-Forwarded-For -> client.host
    if body_ip:
        return body_ip
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # XFF may contain comma separated list; left-most is client
        return xff.split(",")[0].strip()
    return request.client.host

# helper: API key verification
async def verify_api_key(x_api_key: str | None = Header(None)):
    if not SHIELD_API_KEY:
        # dev mode: no key required
        return
    if not x_api_key or x_api_key != SHIELD_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# small UA suspicious check
SUSPICIOUS_UA_RE = re.compile(
    r"(curl|wget|python-requests|libwww-perl|nikto|nmap|sqlmap|headless|phantomjs|puppeteer|crawler|httpclient)",
    re.I,
)

@app.post("/event")
async def event(request: Request, x_api_key: str | None = Header(None)):
    await verify_api_key(x_api_key)

    data = await request.json()
    body_ip = data.get("ip")  # optional
    payload = data.get("payload") or ""
    endpoint = data.get("endpoint", "/")
    ua = request.headers.get("user-agent", "") or ""
    ip = get_client_ip(request, body_ip)

    # quick local preexisting block check
    if local_block.is_blocked(ip):
        log_attack(ip, str(payload) + " | reason: local_block_preexisting", "local_block_preexisting", 1)
        return {"attack_type": "local_block_preexisting", "blocked": True, "reasons": ["local_block_preexisting"]}

    # 1) Signature detection (deterministic)
    sig = detect_signature(str(payload))
    sig_reasons = []
    if sig:
        sig_reasons.append(f"signature:{sig}")

    # 2) Behaviour detection (rate limits / endpoint scanning)
    beh = detect_behaviour(ip, endpoint)
    beh_reasons = []
    if beh:
        beh_reasons.append(f"behaviour:{beh}")

    # 3) Anomaly detection (entropy, repeated payloads, rare endpoints, honeypot)
    anomaly, anomaly_reasons = detect_anomaly(ip, str(payload), endpoint)
    # anomaly may be None or a label and anomaly_reasons list

    # 4) UA-based quick checks (treated as anomalies)
    ua_reasons = []
    if not ua or ua.strip() == "":
        ua_reasons.append("ua_missing")
    elif SUSPICIOUS_UA_RE.search(ua):
        ua_reasons.append("ua_suspicious")

    # Combine reasons
    reasons = []
    reasons.extend(sig_reasons)
    reasons.extend(beh_reasons)
    if anomaly_reasons:
        # detector returns reasons list; ensure type
        if isinstance(anomaly_reasons, list):
            reasons.extend(anomaly_reasons)
        else:
            reasons.append(str(anomaly_reasons))
    reasons.extend(ua_reasons)

    # Decide attack_type and blocking policy (priority)
    # Priority: signature -> high/zero_day_anomaly -> behaviour -> medium anomaly -> None
    attack_type = None
    blocked = 0

    # If signature matched, mark as that (highest trust)
    if sig:
        attack_type = sig

    # If anomaly is high-risk or zero_day_like, escalate
    if not attack_type and anomaly:
        if anomaly in ("zero_day_like", "high_risk"):
            attack_type = anomaly

    # If behaviour detected and nothing higher, set attack_type
    if not attack_type and beh:
        attack_type = beh

    # If still nothing but anomaly medium risk, mark it (no auto-block)
    if not attack_type and anomaly:
        if anomaly == "medium_risk":
            attack_type = "medium_risk"

    # Special: UA-only suspicious (no payload/behaviour) -> mark as ua_suspicious (no auto-block)
    if not attack_type and ua_reasons:
        attack_type = "ua_suspicious"

    # Final blocking decision:
    # auto-block if: signature present OR behaviour detected OR anomaly is high-risk/zero-day
    try:
        if attack_type:
            if sig or beh or (anomaly in ("high_risk", "zero_day_like")):
                # perform block (Cloudflare if configured; falls back to local)
                block_ip(ip, attack_type)
                blocked = 1
            else:
                # medium risk or UA suspicious only -> no auto-block, just log/flag
                blocked = 0
    except Exception as e:
        # if block call throws, still mark as blocked if local fallback set inside block_ip
        # block_ip already falls back to local block on CF failure
        blocked = 1
        reasons.append(f"block_exception:{e}")

    # Log attack with reasons for audit — append reasons into payload for DB
    reason_str = "|".join(reasons) if reasons else ""
    log_payload = f"{str(payload)} | reasons:{reason_str}"
    log_attack(ip, log_payload, attack_type, blocked)

    # Construct response
    resp = {
        "attack_type": attack_type,
        "blocked": bool(blocked),
        "reasons": reasons,
    }
    return resp

# -------------------------
# Unblock endpoint and blocked list
# -------------------------
@app.post("/unblock")
async def api_unblock(request: Request, x_api_key: str | None = Header(None)):
    await verify_api_key(x_api_key)
    data = await request.json()
    ip = data.get("ip")
    if not ip:
        raise HTTPException(status_code=400, detail="Missing ip in body")
    res = unblock_ip(ip)
    log_attack(ip, f"unblock_requested result={res}", "unblock_action", 0)
    return {"result": res}

@app.get("/blocked")
async def api_blocked(x_api_key: str | None = Header(None)):
    await verify_api_key(x_api_key)
    local = list_local_blocks()
    return {"local_blocks": local}