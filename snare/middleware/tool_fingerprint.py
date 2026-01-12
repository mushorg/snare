# snare/middleware/tool_fingerprint.py

import re
from typing import Dict

# Simple rule-based fingerprinting (extensible)
TOOL_RULES = [
    {
        "tool": "dirsearch",
        "patterns": [
            r"dirsearch",
        ],
        "confidence": 0.95,
    },
    {
        "tool": "gobuster",
        "patterns": [
            r"gobuster",
        ],
        "confidence": 0.95,
    },
    {
        "tool": "ffuf",
        "patterns": [
            r"ffuf",
        ],
        "confidence": 0.95,
    },
    {
        "tool": "nikto",
        "patterns": [
            r"nikto",
        ],
        "confidence": 0.95,
    },
    {
        "tool": "curl",
        "patterns": [
            r"curl/",
        ],
        "confidence": 0.6,
    },
    {
        "tool": "python-requests",
        "patterns": [
            r"python-requests",
        ],
        "confidence": 0.7,
    },
]

def fingerprint_tool(user_agent: str, path: str) -> Dict:
    """
    Passive fingerprinting based on User-Agent and request path.
    Returns enrichment dict or empty dict.
    """
    ua = (user_agent or "").lower()

    for rule in TOOL_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, ua):
                return {
                    "tool": rule["tool"],
                    "phase": "recon",
                    "confidence": rule["confidence"],
                }

    # heuristic: aggressive wordlist paths
    if path and len(path) > 20 and path.count("/") >= 3:
        return {
            "tool": "unknown-scanner",
            "phase": "recon",
            "confidence": 0.4,
        }

    return {}
