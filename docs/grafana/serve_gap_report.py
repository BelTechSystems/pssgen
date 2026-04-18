#!/usr/bin/env python3
"""Serve gap_report.json as a Grafana-compatible JSON endpoint.
Reads gap_report.json from the current working directory.
"""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3001

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with open("gap_report.json", "r", encoding="utf-8") as f:
                body = f.read().encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass

HTTPServer(("", PORT), Handler).serve_forever()