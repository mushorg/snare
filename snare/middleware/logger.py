import time
import json
import uuid

# session sederhana per IP (sementara, nanti pindah Redis)
ATTACKER_SESSIONS = {}

@web.middleware
async def logging_middleware(request, handler):
    start_time = time.time()

    peername = request.transport.get_extra_info("peername")
    ip = peername[0] if peername else "unknown"

    ua = request.headers.get("User-Agent", "")
    method = request.method
    path = request.path
    query = dict(request.query)

    session = ATTACKER_SESSIONS.setdefault(ip, {
        "session_id": str(uuid.uuid4()),
        "last_seen": None,
        "requests": []
    })

    now = time.time()
    delta_ms = None
    if session["last_seen"] is not None:
        delta_ms = round((now - session["last_seen"]) * 1000, 2)

    session["last_seen"] = now

    event = {
        "ts": now,
        "ip": ip,
        "method": method,
        "path": path,
        "query": query,
        "user_agent": ua,
        "delta_ms": delta_ms
    }

    session["requests"].append(event)

    # tulis ke file log (JSONL)
    try:
        with open("/var/log/tanner/snare_requests.log", "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        # logging tidak boleh mematikan SNARE
        pass

    response = await handler(request)
    return response
