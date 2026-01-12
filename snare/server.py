import os
import re
import json
import time
import uuid
import random
import logging
import asyncio

from aiohttp import web
from snare.middleware.logger import logging_middleware
from snare.middleware.server_header import server_header_middleware
from snare.tanner_handler import TannerHandler


# =========================================================
# Credential scoring (adaptive realism)
# =========================================================
def credential_score(username, password):
    score = 0

    if re.match(r"^[a-z][a-z0-9._-]{3,20}$", username):
        score += 2
    if len(password) >= 10:
        score += 2
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[0-9]", password):
        score += 1
    if re.search(r"[@#\\-_$!]", password):
        score += 1

    return score


class HttpRequestHandler:
    def __init__(self, meta, run_args, snare_uuid, **kwargs):
        self.run_args = run_args
        self.dir = run_args.full_page_path
        self.meta = meta
        self.snare_uuid = snare_uuid

        self.logger = logging.getLogger("SNARE-AUDIT")
        self.tanner_handler = TannerHandler(run_args, meta, snare_uuid)

        self.sessions = {}
        self.sensitive_paths = {"/admin", "/.git", "/config", "/backup"}

    # =====================================================
    # Unified audit logger (JSON)
    # =====================================================
    def audit(self, request, event, extra=None):
        payload = {
            "event": event,
            "ip": request.remote,
            "method": request.method,
            "path": request.path_qs,
            "ua": request.headers.get("User-Agent"),
            "time": time.time(),
            "session": request.cookies.get("session_id"),
        }
        if extra:
            payload.update(extra)

        self.logger.warning(json.dumps(payload))

    # =====================================================
    async def handle_request(self, request):
        # -------------------------------------------------
        # Tanner side-channel (network telemetry)
        # -------------------------------------------------
        try:
            data = self.tanner_handler.create_data(request, 200)
            if request.method == "POST":
                data["post_data"] = dict(await request.post())
            await self.tanner_handler.submit_data(data)
        except Exception:
            pass

        path = request.path.rstrip("/") or "/"
        ua = request.headers.get("User-Agent", "").lower()

        # -------------------------------------------------
        # Scanner fingerprint delay (soft)
        # -------------------------------------------------
        if any(x in ua for x in ["dirsearch", "ffuf", "gobuster", "sqlmap"]):
            await asyncio.sleep(0.2)

        # =================================================
        # LANDING
        # =================================================
        if path == "/":
            page = self.meta.get("/index.html") or next(iter(self.meta.values()))
            return web.Response(
                body=open(os.path.join(self.dir, page["hash"]), "rb").read(),
                content_type="text/html",
            )

        # =================================================
        # CONSOLE
        # =================================================
        if path == "/console" and request.method == "GET":
            self.audit(request, "view_console")
            page = self.meta.get("/console.html")
            return web.Response(
                body=open(os.path.join(self.dir, page["hash"]), "rb").read(),
                content_type="text/html",
            )

        # =================================================
        # AUTH
        # =================================================
        if path == "/console/auth" and request.method == "POST":
            form = await request.post()
            username = form.get("username", "")
            password = form.get("password", "")

            score = credential_score(username, password)
            self.audit(request, "auth_attempt", {
                "username": username,
                "score": score,
            })

            # Fast fail (junk credential)
            if score < 4:
                return web.HTTPFound("/console?err=auth")

            # Human delay
            await asyncio.sleep(random.uniform(0.8, 1.5))

            # Fake success
            if score >= 6 and random.random() < 0.25:
                session_id = str(uuid.uuid4())
                self.sessions[session_id] = {
                    "username": username,
                    "ip": request.remote,
                    "created": time.time(),
                }

                self.audit(request, "auth_fake_success", {
                    "username": username,
                    "session": session_id,
                })

                resp = web.HTTPFound("/dashboard")
                resp.set_cookie(
                    "session_id",
                    session_id,
                    httponly=True,
                    samesite="Strict",
                )
                return resp

            self.audit(request, "auth_fail_slow", {"username": username})
            return web.HTTPFound("/console?err=auth")

        # =================================================
        # DASHBOARD
        # =================================================
        if path == "/dashboard":
            sess = request.cookies.get("session_id")
            if not sess or sess not in self.sessions:
                return web.HTTPFound("/console")

            self.audit(request, "dashboard_access", {
                "username": self.sessions[sess]["username"]
            })

            page = self.meta.get("/dashboard.html")
            return web.Response(
                body=open(os.path.join(self.dir, page["hash"]), "rb").read(),
                content_type="text/html",
            )

        # =================================================
        # 🔥 OPSI 2: AUDIT EVENT SINK
        # =================================================
        if path == "/audit/event" and request.method == "POST":
            try:
                payload = await request.json()
            except Exception:
                payload = await request.text()

            self.audit(
                request,
                "client_side_audit_event",
                {
                    "payload": payload,
                },
            )

            return web.json_response(
                {"status": "received"},
                headers={
                    "X-Audit-Node": "sfm-collector-01",
                    "X-Audit-Version": "1.2",
                },
            )

        # =================================================
        # API SURFACE
        # =================================================
        if path.startswith("/api"):
            self.audit(request, "api_access")
            if path == "/api/health":
                return web.json_response(
                    {"status": "ok", "node": "sfm-ap-01"},
                    headers={
                        "X-Service-Version": "3.4.1",
                        "X-Backend": "synapse-core",
                    },
                )
            return web.json_response({"error": "access_denied"}, status=403)

        # =================================================
        # HIGH INTEREST
        # =================================================
        if path in self.sensitive_paths:
            self.audit(request, "sensitive_probe")
            await asyncio.sleep(0.1)
            return web.Response(status=403, text="Forbidden")

        # =================================================
        # CLEAN 404
        # =================================================
        self.audit(request, "404")
        return web.Response(status=404, text="Not Found")

    async def start(self):
        app = web.Application(
            middlewares=[logging_middleware, server_header_middleware]
        )
        app.add_routes([web.route("*", "/{tail:.*}", self.handle_request)])

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(
            runner,
            self.run_args.host_ip,
            int(self.run_args.port),
        )
        await site.start()

        print(f"🔥 SNARE ACTIVE @ {self.run_args.host_ip}:{self.run_args.port}")
