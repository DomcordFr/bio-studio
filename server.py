#!/usr/bin/env python3
"""
Bio Studio Companion Server & Static Host
Provides local static hosting, optional zero-CORS JanitorAI API proxy,
and automated Cloudflare Turnstile challenge solving via solver.lucidfr.site.
All authentication tokens remain in-memory and are never written to disk or logs.
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import json
import re
import sys
import os
import time
import threading

PORT = 8080
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    PORT = int(sys.argv[1])
elif "--port" in sys.argv:
    idx = sys.argv.index("--port")
    if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
        PORT = int(sys.argv[idx + 1])
else:
    PORT = int(os.environ.get("PORT", 8080))

DIRECTORY = os.path.dirname(os.path.abspath(__file__))

JANITOR_GATEWAY_URL = "https://janitorai.com/mb"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1jbXp4dHpvbW1wbnhreW5kZGJvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjgzNzA3NDAsImV4cCI6MjA0Mzk0Njc0MH0."
    "UfRPni4ga9Lmin8j0JjV5ouuK9bXp8tsqPJ8pMTDDAI"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

UUID_PATTERN = re.compile(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")

# Cloudflare Turnstile Solver Configuration
SOLVER_URL = os.environ.get("SOLVER_URL", "https://solver.lucidfr.site/solve")
TURNSTILE_SITEKEY = os.environ.get("TURNSTILE_SITEKEY", "0x4AAAAAAAzVax30l5mXO_ul")
TURNSTILE_ACTION = os.environ.get("TURNSTILE_ACTION", "cloudflare-waf")


def get_solver_api_key():
    """
    Retrieves Turnstile solver API key from environment variable or secure local key file.
    Never logs or persists keys.
    """
    env_key = os.environ.get("SOLVER_API_KEY", "").strip()
    if env_key:
        return env_key
    paths = [
        os.path.join(DIRECTORY, "solver_key.txt"),
        "/home/opc/BioStudioBackend/solver_key.txt",
        "/storage/emulated/0/gemini/Outputs/bio-studio/solver_key.txt",
        "/storage/emulated/0/gemini/solver_key.txt",
        "/storage/emulated/0/gemini/Credentials/solver_key.txt"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("sk-"):
                    return content
            except Exception:
                continue
    return ""


_turnstile_lock = threading.Lock()
_turnstile_cache = {
    "token": None,
    "expires_at": 0,
    "last_ms": 0,
    "last_id": None
}


def get_turnstile_token(force_refresh=False):
    """
    Fetches or returns cached Cloudflare Turnstile token from solver.lucidfr.site.
    Caches token for 180 seconds (~3 minutes) to avoid redundant solver latency.
    """
    now = time.time()
    with _turnstile_lock:
        if not force_refresh and _turnstile_cache["token"] and _turnstile_cache["expires_at"] > now:
            return _turnstile_cache["token"]

    api_key = get_solver_api_key()
    if not api_key:
        return None

    try:
        payload = json.dumps({
            "url": "https://janitorai.com/",
            "sitekey": TURNSTILE_SITEKEY,
            "action": TURNSTILE_ACTION,
            "timeout_s": 60
        }).encode("utf-8")

        req = urllib.request.Request(
            SOLVER_URL,
            data=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "X-API-Key": api_key
            }
        )
        with urllib.request.urlopen(req, timeout=65) as res:
            data = json.loads(res.read().decode("utf-8"))
            if data.get("ok") and data.get("token"):
                tok = data["token"]
                with _turnstile_lock:
                    _turnstile_cache["token"] = tok
                    _turnstile_cache["expires_at"] = time.time() + 180
                    _turnstile_cache["last_ms"] = data.get("ms", 0)
                    _turnstile_cache["last_id"] = data.get("id")
                print(f"[Solver] Obtained Turnstile token (id: {data.get('id', '-')}, {data.get('ms', 0)}ms)")
                return tok
            else:
                print(f"[Solver] Turnstile solve returned error: {data}")
    except Exception as e:
        print(f"[Solver] Failed to obtain Turnstile token from solver: {e}")
    return None


def get_local_token():
    paths = [
        os.path.join(DIRECTORY, "token.txt"),
        "/home/opc/janitor_session.json",
        "/home/opc/BioStudioBackend/token.txt",
        "/storage/emulated/0/gemini/token.txt",
        "/storage/emulated/0/gemini/Credentials/token.txt",
        "/storage/emulated/0/gemini/Outputs/Cloud - Janitor/session.json"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content.startswith("{"):
                    d = json.loads(content)
                    if d.get("access_token"):
                        return d["access_token"].strip()
                m = re.search(r"eyJ[a-zA-Z0-9_-]{20,}\.eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}", content)
                if m:
                    return m.group(0).strip()
            except Exception:
                continue
    return ""


def execute_janitor_request(target_url, headers, method="GET", data=None):
    """
    Executes request to JanitorAI with Turnstile token and auto-retry on 403 challenge.
    """
    req_headers = dict(headers)
    if "cf-turnstile-response" not in req_headers:
        tok = get_turnstile_token(force_refresh=False)
        if tok:
            req_headers["cf-turnstile-response"] = tok

    req = urllib.request.Request(target_url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.status, response.read(), None
    except urllib.error.HTTPError as e:
        err_body = e.read()
        err_str = err_body.decode("utf-8", errors="replace") if err_body else ""
        is_cf_block = (
            e.code == 403 and (
                "error code: 1010" in err_str or
                e.headers.get("cf-mitigated") == "challenge" or
                "cloudflare" in err_str.lower()
            )
        )
        if is_cf_block:
            print(f"[Gateway] Cloudflare challenge encountered on {target_url}. Requesting fresh Turnstile solve...")
            fresh_tok = get_turnstile_token(force_refresh=True)
            if fresh_tok:
                req_headers["cf-turnstile-response"] = fresh_tok
                retry_req = urllib.request.Request(target_url, data=data, headers=req_headers, method=method)
                try:
                    with urllib.request.urlopen(retry_req, timeout=25) as retry_res:
                        print(f"[Gateway] Retried with fresh Turnstile token: HTTP {retry_res.status} OK")
                        return retry_res.status, retry_res.read(), None
                except urllib.error.HTTPError as re_err:
                    return re_err.code, re_err.read(), re_err
                except Exception as ex:
                    return 502, json.dumps({"error": f"Retry failed: {str(ex)}"}).encode("utf-8"), ex

        return e.code, err_body, e
    except Exception as e:
        return 502, json.dumps({"error": f"Gateway request failed: {str(e)}"}).encode("utf-8"), e


class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, apikey, cf-turnstile-response, Cookie")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/token":
            tok = get_local_token()
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"token": tok}).encode("utf-8"))
            return

        if self.path == "/api/solver/status":
            now = time.time()
            with _turnstile_lock:
                has_cached = bool(_turnstile_cache["token"] and _turnstile_cache["expires_at"] > now)
                expires_in = max(0, int(_turnstile_cache["expires_at"] - now)) if has_cached else 0
                last_ms = _turnstile_cache["last_ms"]
                last_id = _turnstile_cache["last_id"]

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "enabled": bool(get_solver_api_key()),
                "solver_url": SOLVER_URL,
                "cached": has_cached,
                "expires_in_seconds": expires_in,
                "last_solve_ms": last_ms,
                "last_job_id": last_id
            }).encode("utf-8"))
            return

        if self.path.startswith("/api/janitor/characters/"):
            match = UUID_PATTERN.search(self.path)
            if not match:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid character UUID"}).encode("utf-8"))
                return

            char_id = match.group(1).lower()
            auth_header = self.headers.get("Authorization")
            if not auth_header or auth_header == f"Bearer {SUPABASE_ANON_KEY}":
                local_tok = get_local_token()
                auth_header = f"Bearer {local_tok}" if local_tok else f"Bearer {SUPABASE_ANON_KEY}"

            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": auth_header,
                "Origin": "https://janitorai.com",
                "Referer": "https://janitorai.com/"
            }
            # Pass client Turnstile or cookies if explicitly supplied
            if self.headers.get("cf-turnstile-response"):
                headers["cf-turnstile-response"] = self.headers.get("cf-turnstile-response")
            if self.headers.get("Cookie"):
                headers["Cookie"] = self.headers.get("Cookie")

            # Try /hampter first
            target_url = f"https://janitorai.com/hampter/characters/{char_id}"
            status, data, err = execute_janitor_request(target_url, headers, method="GET")

            # Fallback to /mb if /hampter returns 404 or fails
            if status != 200:
                fallback_url = f"{JANITOR_GATEWAY_URL}/characters/{char_id}"
                f_status, f_data, f_err = execute_janitor_request(fallback_url, headers, method="GET")
                if f_status == 200:
                    status, data = f_status, f_data

            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/api/status":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "online",
                "version": "2.1.0",
                "companion": True,
                "proxyAvailable": True,
                "turnstileSolver": bool(get_solver_api_key())
            }).encode("utf-8"))
            return

        # SPA client-side routes fallback
        spa_routes = {"/overview", "/studio", "/prompts", "/guide", "/decoder", "/privacy"}
        clean_path = self.path.split("?")[0].rstrip("/")
        if clean_path in spa_routes:
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/solver/solve":
            tok = get_turnstile_token(force_refresh=True)
            self.send_response(200 if tok else 502)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if tok:
                self.wfile.write(json.dumps({"ok": True, "token": tok}).encode("utf-8"))
            else:
                self.wfile.write(json.dumps({"ok": False, "error": "Solver failed to obtain token"}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        if self.path.startswith("/api/janitor/characters/"):
            match = UUID_PATTERN.search(self.path)
            if not match:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid character UUID"}).encode("utf-8"))
                return

            char_id = match.group(1).lower()
            auth_header = self.headers.get("Authorization")
            if not auth_header or auth_header == f"Bearer {SUPABASE_ANON_KEY}":
                local_tok = get_local_token()
                if local_tok:
                    auth_header = f"Bearer {local_tok}"

            if not auth_header or not auth_header.startswith("Bearer "):
                self.send_response(401)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Authentication token required for updating character bio"}).encode("utf-8"))
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            target_url = f"{JANITOR_GATEWAY_URL}/characters/{char_id}"
            headers = {
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": auth_header,
                "Origin": "https://janitorai.com",
                "Referer": f"https://janitorai.com/characters/{char_id}"
            }
            if self.headers.get("cf-turnstile-response"):
                headers["cf-turnstile-response"] = self.headers.get("cf-turnstile-response")
            if self.headers.get("Cookie"):
                headers["Cookie"] = self.headers.get("Cookie")

            status, data, err = execute_janitor_request(target_url, headers, method="PATCH", data=body)

            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(404)
        self.end_headers()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def run():
    with ThreadedTCPServer(("", PORT), StudioHandler) as httpd:
        print(f"Bio Studio Companion Server running at http://127.0.0.1:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    run()
