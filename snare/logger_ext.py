import json
import time
from pathlib import Path

LOG_DIR = Path("/var/log/snare")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_event(filename: str, payload: dict):
    payload["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG_DIR / filename, "a") as f:
        f.write(json.dumps(payload) + "\n")
