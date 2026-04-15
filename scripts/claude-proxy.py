#!/usr/bin/env python3
"""
Host-side Claude CLI proxy for contract-sentry PoC generation.

Exposes a local HTTP server that wraps `claude -p` so Docker containers
can call it via host.docker.internal.

Usage:
    python3 scripts/claude-proxy.py          # default port 9876
    python3 scripts/claude-proxy.py 9876
"""
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9876


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # suppress default access log
        pass

    def do_POST(self):
        if self.path != "/generate":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        prompt = body.get("prompt", "")

        try:
            proc = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                payload = {"poc": None, "error": proc.stderr.strip()[:500]}
            else:
                payload = {"poc": proc.stdout.strip(), "error": None}
        except FileNotFoundError:
            payload = {"poc": None, "error": "claude CLI not found on PATH"}
        except subprocess.TimeoutExpired:
            payload = {"poc": None, "error": "claude CLI timed out"}

        response = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Claude proxy listening on 0.0.0.0:{PORT} — Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
