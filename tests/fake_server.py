#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import time


def embedding(text: str) -> list[float]:
    raw = [float(len(text) + 1), float(sum(map(ord, text)) % 997 + 1), float(text.count(" ") + 1), 1.0]
    norm = math.sqrt(sum(value * value for value in raw))
    return [value / norm for value in raw]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self._json(200, {"status": "ok"})

    def do_POST(self) -> None:
        if self.path != "/embed":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size))
        inputs = payload["inputs"]
        if inputs == "":
            self._json(400, {"error": "`inputs` cannot be empty", "error_type": "validation"})
            return
        texts = inputs if isinstance(inputs, list) else [inputs]
        self._json(200, [embedding(text) for text in texts])

    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--startup-delay-ms", type=float, default=0)
    args = parser.parse_args()
    time.sleep(args.startup_delay_ms / 1000)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
