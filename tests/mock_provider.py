"""A minimal Anthropic-compatible mock server that records request headers.

Used by tests to verify the settings ccmp writes actually drive Claude Code
without spending real tokens.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockProvider:
    def __init__(self, port: int = 0):
        self.requests: list[dict] = []
        self._httpd = HTTPServer(("127.0.0.1", port), self._handler())
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: ARG002
                pass

            def do_POST(self):
                length = int(self.headers.get("content-length") or 0)
                self.rfile.read(length)
                outer.requests.append(
                    {
                        "path": self.path,
                        "authorization": self.headers.get("authorization"),
                        "x_api_key": self.headers.get("x-api-key"),
                    }
                )
                body = json.dumps(
                    {
                        "id": "msg_mock",
                        "type": "message",
                        "role": "assistant",
                        "model": "mock",
                        "content": [{"type": "text", "text": "ok"}],
                        "stop_reason": "end_turn",
                        "stop_sequence": None,
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                ).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler

    def start(self) -> "MockProvider":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
