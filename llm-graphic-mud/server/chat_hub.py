"""프록시의 온라인 채팅. HTTP 스트리밍 (표준 라이브러리만).

WebSocket 대신 쓰는 이유: ngrok 무료판 경고 페이지가 WebSocket 연결을 가로채는데,
브라우저 WebSocket 은 우회 헤더(ngrok-skip-browser-warning)를 못 붙인다. fetch 는 붙일 수 있다.

GET  /chat/stream?nick=..   길게 열린 응답. 한 줄에 JSON 하나 (NDJSON)
     {"type":"hello", "sid", "nick", "history":[...]}
     {"type":"chat", "nick", "text", "ts"}
     {"type":"notice", "text"}            입장 · 퇴장
     {"type":"presence", "nicks":[...]}
     {"type":"ping"}                      20초마다 (연결 유지 · 끊김 감지)
POST /chat/send  {"sid", "text"}

키 확인은 proxy.py 가 먼저 한다 (X-Proxy-Key 헤더).
"""
import json
import queue
import secrets
import select
import socket
import threading
import time
from collections import deque

HEARTBEAT = 20
CHAT_MAX = 500
CHAT_BURST = (10, 10)       # 10초에 10줄까지
NICK_MAX = 16

_history = deque(maxlen=50)
_subs = {}                  # sid → Sub
_lock = threading.Lock()


class Sub:
    def __init__(self, nick):
        self.sid = secrets.token_urlsafe(12)
        self.nick = nick
        self.q = queue.Queue(maxsize=500)
        self.hits = deque()

    def push(self, obj):
        try:
            self.q.put_nowait(obj)
        except queue.Full:
            pass                # 못 받아가는 연결은 버린다

    def chat_ok(self):
        now = time.monotonic()
        while self.hits and now - self.hits[0] > CHAT_BURST[1]:
            self.hits.popleft()
        if len(self.hits) >= CHAT_BURST[0]:
            return False
        self.hits.append(now)
        return True


def _broadcast(obj):
    with _lock:
        subs = list(_subs.values())
    for s in subs:
        s.push(obj)


def _presence():
    with _lock:
        nicks = sorted(s.nick for s in _subs.values())
    _broadcast({"type": "presence", "nicks": nicks})


def stream(handler, nick):
    """GET /chat/stream — 연결이 끊길 때까지 돌려보내지 않는다."""
    nick = " ".join(str(nick or "").split())[:NICK_MAX] or "손님"
    sub = Sub(nick)

    handler.send_response(200)
    handler.cors()
    handler.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Accel-Buffering", "no")
    handler.send_header("Transfer-Encoding", "chunked")
    handler.end_headers()
    handler.close_connection = True

    def write(obj):
        line = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        handler.wfile.write(b"%x\r\n%s\r\n" % (len(line), line))
        handler.wfile.flush()

    with _lock:
        hist = list(_history)
        _subs[sub.sid] = sub
    try:
        write({"type": "hello", "sid": sub.sid, "nick": nick, "history": hist})
        _broadcast({"type": "notice", "text": f"{nick} 님이 들어왔다"})
        _presence()
        sock = handler.connection
        last = time.monotonic()
        while True:
            try:
                write(sub.q.get(timeout=1))
                last = time.monotonic()
            except queue.Empty:
                pass
            # 브라우저가 끊으면 소켓이 읽을 거리(EOF)를 내놓는다 — 1초 안에 알아챈다
            if select.select([sock], [], [], 0)[0] and not sock.recv(1, socket.MSG_PEEK):
                break
            if time.monotonic() - last > HEARTBEAT:
                write({"type": "ping"})
                last = time.monotonic()
    except OSError:
        pass
    finally:
        with _lock:
            _subs.pop(sub.sid, None)
        _broadcast({"type": "notice", "text": f"{nick} 님이 나갔다"})
        _presence()


def send(body):
    """POST /chat/send → (상태 코드, 응답)"""
    try:
        msg = json.loads(body or b"{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"error": "bad json"}
    with _lock:
        sub = _subs.get(str(msg.get("sid")))
    if not sub:
        return 409, {"error": "not connected"}
    text = str(msg.get("text") or "").strip()[:CHAT_MAX]
    if not text:
        return 400, {"error": "empty"}
    if not sub.chat_ok():
        return 429, {"error": "너무 빨리 보내고 있다"}
    line = {"type": "chat", "nick": sub.nick, "text": text, "ts": int(time.time() * 1000)}
    with _lock:
        _history.append(line)
    _broadcast(line)
    return 200, {"ok": True}
