"""llm-graphic-mud 로컬 프록시.

GitHub Pages 프론트 → ngrok → 이 프록시(127.0.0.1:8787) → Ollama · ComfyUI.

- 키 확인: 요청마다 `X-Proxy-Key` 헤더. 키는 server/proxy.key (없으면 새로 만든다, 커밋 안 함).
- 허용 경로만 통과시킨다. 나머지는 404.
- CORS: ALLOWED_ORIGINS 만.
- 분당 요청 수 제한.
- 파이썬 표준 라이브러리만 쓴다.
- /chat/stream · /chat/send : 온라인 채팅 (chat_hub.py, HTTP 스트리밍).

실행: python server/proxy.py   (또는 server/start.ps1 로 ngrok 까지)
"""
import hmac
import http.client
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import chat_hub

HOST, PORT = "127.0.0.1", int(os.environ.get("MUD_PROXY_PORT", 8787))
OLLAMA = ("127.0.0.1", 11434)
COMFY = ("127.0.0.1", 8188)

ALLOWED_ORIGINS = {
    "https://game.onethelab.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8765",   # repo 루트 개발 서버 (.claude/launch.json)
    "http://127.0.0.1:8765",
}
ALLOWED_HEADERS = "Content-Type, X-Proxy-Key, ngrok-skip-browser-warning"

RATE_LIMIT = 120          # 분당 요청 수 (OPTIONS · /health 제외)
MAX_BODY = 4 * 1024 * 1024
UPSTREAM_TIMEOUT = 600    # 그림 · 긴 답변 기다림

KEY_FILE = Path(__file__).with_name("proxy.key")

# (메서드, 경로 정규식, 업스트림, 업스트림 경로 만들기)
ROUTES = [
    ("POST", r"/ollama/api/chat", OLLAMA, lambda m: "/api/chat"),
    ("GET", r"/ollama/api/tags", OLLAMA, lambda m: "/api/tags"),
    ("POST", r"/comfy/prompt", COMFY, lambda m: "/prompt"),
    ("GET", r"/comfy/history/([0-9a-fA-F-]{1,64})", COMFY, lambda m: f"/history/{m.group(1)}"),
    ("GET", r"/comfy/view", COMFY, lambda m: "/view"),
    ("GET", r"/comfy/queue", COMFY, lambda m: "/queue"),
]
ROUTES = [(meth, re.compile(pat + r"$"), up, build) for meth, pat, up, build in ROUTES]


def load_key():
    if not KEY_FILE.exists():
        KEY_FILE.write_text(secrets.token_urlsafe(24), encoding="utf-8")
        print(f"[proxy] 새 키를 만들었다: {KEY_FILE}")
    return KEY_FILE.read_text(encoding="utf-8").strip()


KEY = load_key()

_hits = deque()
_hits_lock = threading.Lock()


def rate_ok():
    now = time.monotonic()
    with _hits_lock:
        while _hits and now - _hits[0] > 60:
            _hits.popleft()
        if len(_hits) >= RATE_LIMIT:
            return False
        _hits.append(now)
        return True


def view_query_ok(query):
    """ComfyUI /view 는 output · temp 폴더의 그림만."""
    q = parse_qs(query)
    if q.get("type", ["output"])[0] not in ("output", "temp"):
        return False
    for k in ("filename", "subfolder"):
        for v in q.get(k, []):
            if ".." in v or v.startswith(("/", "\\")) or ":" in v:
                return False
    return bool(q.get("filename"))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "mud-proxy"

    # ---- 공통 ----
    def cors(self):
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def reply_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # 키 · 쿼리는 찍지 않는다
        sys.stderr.write("[proxy] %s %s\n" % (self.command, urlsplit(self.path).path) + "  " + (fmt % args) + "\n")

    # ---- 메서드 ----
    def do_OPTIONS(self):
        origin = self.headers.get("Origin")
        if origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(204)
        self.cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", ALLOWED_HEADERS)
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self.handle_proxy()

    def do_POST(self):
        self.handle_proxy()

    # ---- 본체 ----
    def handle_proxy(self):
        url = urlsplit(self.path)
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return self.reply_json(403, {"error": "origin not allowed"})

        if url.path == "/health":
            return self.reply_json(200, {"ok": True})

        if not hmac.compare_digest(self.headers.get("X-Proxy-Key", ""), KEY):
            return self.reply_json(401, {"error": "bad key"})

        if url.path in ("/chat/stream", "/chat/send"):
            if not rate_ok():
                return self.reply_json(429, {"error": "too many requests"})
            if url.path == "/chat/stream" and self.command == "GET":
                return chat_hub.stream(self, parse_qs(url.query).get("nick", [""])[0])
            if url.path == "/chat/send" and self.command == "POST":
                n = int(self.headers.get("Content-Length") or 0)
                if n > 16 * 1024:
                    return self.reply_json(413, {"error": "body too large"})
                return self.reply_json(*chat_hub.send(self.rfile.read(n)))
            return self.reply_json(405, {"error": "method"})

        for meth, pat, upstream, build in ROUTES:
            m = pat.match(url.path)
            if m and meth == self.command:
                break
        else:
            return self.reply_json(404, {"error": "not allowed"})

        if url.path == "/comfy/view" and not view_query_ok(url.query):
            return self.reply_json(400, {"error": "bad view query"})

        if not rate_ok():
            return self.reply_json(429, {"error": "too many requests"})

        body = None
        if self.command == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self.reply_json(413, {"error": "body too large"})
            body = self.rfile.read(n)

        path = build(m) + (("?" + url.query) if url.query else "")
        try:
            conn = http.client.HTTPConnection(*upstream, timeout=UPSTREAM_TIMEOUT)
            # Origin · Host 는 넘기지 않는다 (업스트림의 출처 검사에 걸리지 않게)
            headers = {"Content-Type": self.headers.get("Content-Type", "application/json")} if body is not None else {}
            conn.request(self.command, path, body=body, headers=headers)
            resp = conn.getresponse()
        except OSError as e:
            return self.reply_json(502, {"error": f"upstream: {e}"})

        # 스트리밍 그대로 흘려보낸다 (chunked)
        self.send_response(resp.status)
        self.cors()
        self.send_header("Content-Type", resp.getheader("Content-Type", "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            while True:
                chunk = resp.read1(65536)
                if not chunk:
                    break
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            conn.close()


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[proxy] http://{HOST}:{PORT}  →  ollama {OLLAMA[1]} · comfy {COMFY[1]}")
    print(f"[proxy] 키 파일: {KEY_FILE}")
    print(f"[proxy] 키: {KEY}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
