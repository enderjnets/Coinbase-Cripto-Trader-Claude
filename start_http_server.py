#!/usr/bin/env python3
"""
Inicia el servidor HTTP para servir datos a los workers
"""

import os
import http.server
import socketserver

PORT = 8765
STATIC_DIR = os.path.join(os.getcwd(), "static_payloads")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

print(f"Starting HTTP server on port {PORT}")
print(f"Serving files from: {STATIC_DIR}")
print(f"Press Ctrl+C to stop\n")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://0.0.0.0:{PORT}/")
    httpd.serve_forever()
