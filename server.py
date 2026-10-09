#!/usr/bin/env python3
"""
Bio Studio Companion Server & Static Host
Provides local static hosting and optional zero-CORS JanitorAI API proxy.
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


class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, apikey")

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
            
            # Primary read gateway for public character data is /hampter
            target_url = f"https://janitorai.com/hampter/characters/{char_id}"
            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": auth_header,
                    "Origin": "https://janitorai.com",
                    "Referer": "https://janitorai.com/"
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    data = response.read()
                    self.send_response(response.status)
                    self._send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(data)
            except urllib.error.HTTPError as e:
                # Fallback to /mb if /hampter fails
                try:
                    fallback_url = f"{JANITOR_GATEWAY_URL}/characters/{char_id}"
                    f_req = urllib.request.Request(
                        fallback_url,
                        headers={
                            "User-Agent": USER_AGENT,
                            "Accept": "application/json, text/plain, */*",
                            "apikey": SUPABASE_ANON_KEY,
                            "Authorization": auth_header,
                            "Origin": "https://janitorai.com",
                            "Referer": "https://janitorai.com/"
                        }
                    )
                    with urllib.request.urlopen(f_req, timeout=20) as f_res:
                        data = f_res.read()
                        self.send_response(f_res.status)
                        self._send_cors_headers()
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                except Exception:
                    pass

                err_body = e.read()
                self.send_response(e.code)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(err_body if err_body else json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception as e:
                self.send_response(502)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Gateway request failed: {str(e)}"}).encode("utf-8"))
            return

        if self.path == "/api/status":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "online",
                "version": "2.0.0",
                "companion": True,
                "proxyAvailable": True
            }).encode("utf-8"))
            return

        super().do_GET()

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
            req = urllib.request.Request(
                target_url,
                data=body,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/plain, */*",
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": auth_header,
                    "Origin": "https://janitorai.com",
                    "Referer": f"https://janitorai.com/characters/{char_id}"
                },
                method="PATCH"
            )

            try:
                with urllib.request.urlopen(req, timeout=25) as response:
                    data = response.read()
                    self.send_response(response.status)
                    self._send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(data)
            except urllib.error.HTTPError as e:
                err_body = e.read()
                self.send_response(e.code)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(err_body if err_body else json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception as e:
                self.send_response(502)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Gateway patch failed: {str(e)}"}).encode("utf-8"))
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
