"""Cairn — 플레이 블러드 올름 서버.

Claude(claude-opus-5-5)가 워든이 되어 CAS-2 블러드 올름을 진행한다.
접속자 모두가 한 방에서 채팅하고, '마스터에게' 보낸 말에 워든이 답한다.

채팅은 HTTP 스트리밍 (llm-graphic-mud 와 같은 이유: ngrok 무료판 경고 페이지가
WebSocket 을 가로채고, 브라우저 WebSocket 은 우회 헤더를 못 붙인다).

POST /api/join    {"password", "nick"}          → {"token", "nick", "color"}
GET  /api/stream  헤더 X-Token                  → NDJSON 한 줄에 하나
     {"type":"hello", "me":{nick,color}, "log":[...], "gm_busy"}
     {"type":"chat", "nick", "color", "text", "to_gm", "ts"}
     {"type":"gm_start"} {"type":"gm_delta","text"} {"type":"gm_end"}   (기록에는 {"type":"gm","text"} 토막)
     {"type":"dice", "expr", "rolls", "total", "why"}
     {"type":"notice", "text"} {"type":"presence", "users":[{nick,color}]} {"type":"ping"}
POST /api/send    헤더 X-Token  {"text", "to_gm"}
GET  /           play.html (이 서버로 바로 들어와도 된다)

비밀: server/cairn.pass (입장 비밀번호, 없으면 12341234 로 만든다)
      ANTHROPIC_API_KEY 환경변수 또는 server/anthropic.key
      둘 다 커밋 안 함 (server/.gitignore). 키가 없으면 흉내 워든(MOCK)으로 돈다.
상태: server/state.json — 워든과의 대화 · 채팅 기록. 서버를 껐다 켜도 이어진다.

실행: python server/cairn_server.py   (또는 server/start.ps1 로 ngrok 까지)
"""
import colorsys
import hmac
import json
import os
import queue
import random
import re
import secrets
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HOST, PORT = "127.0.0.1", int(os.environ.get("CAIRN_PORT", 8790))

MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 16000

ALLOWED_ORIGINS = {
    "https://game.onethelab.com",
    "http://localhost:8765", "http://127.0.0.1:8765",   # repo 루트 개발 서버
    f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}",
}
HEARTBEAT = 20
NICK_MAX, TEXT_MAX = 16, 600
LOG_KEEP = 300                 # 새로 들어온 사람에게 보여 줄 채팅 줄 수
SEND_BURST = (8, 20)           # 20초에 8줄
GM_BURST = (6, 60)             # 한 사람이 1분에 마스터 호출 6번
JOIN_BURST = (6, 60)           # IP 하나가 1분에 입장 시도 6번

PASS_FILE = HERE / "cairn.pass"
KEY_FILE = HERE / "anthropic.key"
STATE_FILE = HERE / "state.json"

# ── 비밀 ─────────────────────────────────────────────
if not PASS_FILE.exists():
    PASS_FILE.write_text("12341234", encoding="utf-8")
PASSWORD = PASS_FILE.read_text(encoding="utf-8").strip()

API_KEY = os.environ.get("ANTHROPIC_API_KEY") or (
    KEY_FILE.read_text(encoding="utf-8").strip() if KEY_FILE.exists() else "")
MOCK = not API_KEY or os.environ.get("CAIRN_MOCK") == "1"

client = None
if not MOCK:
    import anthropic
    client = anthropic.Anthropic(api_key=API_KEY)


# ── 워든 지시문 (한 번 만들고 그대로 — 캐시 접두가 바뀌지 않게) ──
def build_system():
    docs = ROOT / "docs"
    rules = (docs / "룰_요약.md").read_text(encoding="utf-8")
    scen = (docs / "시나리오_블러드올름.md").read_text(encoding="utf-8")
    scen_src = (docs / "src" / "scenario_blood_olms.md").read_text(encoding="utf-8")
    scen_src = re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", scen_src)      # 그림 링크는 뺀다
    guide = """너는 TRPG Cairn 2e 의 워든(마스터)이다. 모듈 CAS-2 「블러드 올름의 부상」을 진행한다.
여러 플레이어가 한 채팅방에 있다. 플레이어의 말은 `[닉네임] 내용` 꼴로 온다. 같은 차례에 여러 명의 말이 함께 올 수 있다.

진행 원칙
- 한국어로, 짧고 생생하게. 한 번에 화면 한두 개 분량. 장면 끝에 무엇을 할지 묻는다.
- 냄새 · 소리 · 온도 · 거리 · 위치를 구체적으로. 감정을 대신 말하지 않는다.
- 위험은 미리 분명하게 알린다. 죽음은 경고 없이 오지 않는다.
- 비밀(진상 · 방의 숨은 내용 · NPC 능력치)은 플레이어가 알아낼 때까지 밝히지 않는다.
- 플레이어가 스스로 정할 일(행동 · 말)을 대신 정하지 않는다. 동료 NPC 는 네가 움직인다.
- 플레이어끼리의 잡담(`(잡담)` 표시)은 맥락으로만 읽고, 따로 답하지 않는다.

주사위
- 결과가 불확실하면 반드시 roll_dice 도구로 굴린다. 결과를 지어내지 않는다.
- 세이브(d20 ≤ 능력치), 피해, 반응(2d6), 운명 주사위(d6), 던전 사건(d6), 캐릭터 생성 모두 도구로.
- 굴린 값과 결과를 서술에 짧게 밝힌다. 예: "DEX 세이브 6 (≤14) 성공".

시작
- 처음 온 플레이어에게는 캐릭터를 만들어 준다: 배경 d20, 능력치 3d6 ×3, HP d6, 특성 · 본드, 나이 2d20+10. 가장 어린 PC 가 오멘 d20.
  배경 표의 세부 항목은 룰 원문이 없으니, 배경 이름과 분위기에 맞게 시작 장비를 3–5개 정해 준다 (무기 하나 · 광원 · 식량 포함).
- 혼자라면 동료 NPC 한 명을 붙여 준다.
- 파티가 갖춰지면 의뢰를 전하고, 도착 시각과 날씨를 묻고 운명 주사위로 비튼다.

상태 표시
- 캐릭터의 HP · 능력치 · 짐 칸 · 광원 횟수가 바뀌면, 답의 맨 끝에 한 줄로 요약한다.
  예: `▸ 아마라 HP 0/2 · STR 9 · 짐 9/10 · 횃불 2 | 세이블 HP 5 · STR 8`
"""
    return [
        {"type": "text", "text": guide},
        {"type": "text", "text": "## 룰 요약\n\n" + rules},
        {"type": "text", "text": "## 시나리오 정리 (워든 전용)\n\n" + scen},
        {"type": "text", "text": "## 시나리오 원문 (워든 전용)\n\n" + scen_src},
    ]


SYSTEM = build_system()

TOOLS = [{
    "name": "roll_dice",
    "description": "주사위를 굴린다. 결과는 방의 모든 플레이어에게 보인다. 세이브 · 피해 · 반응 · 사건 · 캐릭터 생성 등 불확실한 모든 것에 쓴다.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "expr": {"type": "string", "description": "주사위 식. 예: d20, 3d6, 2d6, d8+d8 (두 개 굴려 높은 쪽), d6+2"},
            "why": {"type": "string", "description": "무엇을 위한 굴림인지 짧게. 예: '아마라 DEX 세이브 (14)'"},
        },
        "required": ["expr", "why"],
        "additionalProperties": False,
    },
}]

DICE_RE = re.compile(r"^\s*(\d{0,2})d(\d{1,3})(?:\s*\+\s*(\d{0,2})d(\d{1,3}))?\s*([+-]\s*\d{1,3})?\s*$", re.I)


def roll(expr):
    """'3d6' 합 · 'd8+d8' 둘 중 높은 값 · 'd6+2' 보정."""
    m = DICE_RE.match(expr or "")
    if not m:
        raise ValueError(f"주사위 식을 못 읽음: {expr!r}")
    n1, s1, n2, s2, mod = m.groups()
    n1, s1 = int(n1 or 1), int(s1)
    if not (1 <= n1 <= 20 and 2 <= s1 <= 100):
        raise ValueError("주사위 개수 1–20, 면 2–100")
    a = [random.randint(1, s1) for _ in range(n1)]
    if s2:                                    # d8+d8 — 두 무기, 높은 쪽
        n2 = int(n2 or 1)
        b = [random.randint(1, int(s2)) for _ in range(n2)]
        rolls, total = [a, b], max(sum(a), sum(b))
    else:
        rolls, total = [a], sum(a)
    if mod:
        total += int(mod.replace(" ", ""))
    return rolls, total


# ── 접속자 ───────────────────────────────────────────
class Client:
    def __init__(self, nick, color):
        self.token = secrets.token_urlsafe(18)
        self.nick, self.color = nick, color
        self.q = queue.Queue(maxsize=2000)
        self.online = 0                       # 열린 스트림 수
        self.sends, self.gm_calls = deque(), deque()

    def push(self, obj):
        try:
            self.q.put_nowait(obj)
        except queue.Full:
            pass


def burst_ok(hits, limit):
    n, sec = limit
    now = time.monotonic()
    while hits and now - hits[0] > sec:
        hits.popleft()
    if len(hits) >= n:
        return False
    hits.append(now)
    return True


lock = threading.RLock()
clients = {}                 # token → Client
join_hits = {}               # ip → deque
GM_COLOR = "#c0392b"


def pick_color():
    """지금 있는 색들과 색상환에서 가장 먼 쪽으로."""
    with lock:
        used = [c.hue for c in clients.values() if c.online and hasattr(c, "hue")]
    best, best_d = random.random(), -1
    for _ in range(24):
        h = random.random()
        d = min([min(abs(h - u), 1 - abs(h - u)) for u in used] or [1])
        if d > best_d:
            best, best_d = h, d
    r, g, b = colorsys.hls_to_rgb(best, 0.55, 0.65)
    return best, "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def broadcast(obj, keep=True):
    if keep:
        with lock:
            state["log"].append(obj)
            del state["log"][:-LOG_KEEP]
    with lock:
        targets = [c for c in clients.values() if c.online]
    for c in targets:
        c.push(obj)


def log_only(obj):
    """방송은 이미 조각(gm_delta)으로 했고, 기록에만 통째로 남긴다."""
    if obj.get("text", "").strip():
        with lock:
            state["log"].append(obj)
            del state["log"][:-LOG_KEEP]


def presence():
    with lock:
        users = [{"nick": c.nick, "color": c.color} for c in clients.values() if c.online]
    broadcast({"type": "presence", "users": users}, keep=False)


# ── 상태 저장 ────────────────────────────────────────
state = {"messages": [], "log": []}
if STATE_FILE.exists():
    try:
        state.update(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass


def save_state():
    with lock:
        data = json.dumps(state, ensure_ascii=False)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(STATE_FILE)


# ── 워든 ─────────────────────────────────────────────
pending = []                 # 아직 워든에게 안 간 줄 "[닉] 내용"
pending_act = False          # 그 안에 '마스터에게' 가 하나라도 있나
gm_busy = False


def queue_line(nick, text, to_gm):
    global pending_act
    with lock:
        pending.append(f"[{nick}] {text}" if to_gm else f"(잡담) [{nick}] {text}")
        pending_act = pending_act or to_gm
    kick_gm()


def kick_gm():
    global gm_busy, pending_act
    with lock:
        if gm_busy or not pending_act:
            return
        gm_busy, pending_act = True, False
        lines = pending[:]
        pending.clear()
    threading.Thread(target=gm_turn, args=(lines,), daemon=True).start()


def gm_turn(lines):
    global gm_busy
    with lock:
        state["messages"].append({"role": "user", "content": "\n".join(lines)})
    broadcast({"type": "gm_start"}, keep=False)
    try:
        run_mock() if MOCK else run_claude()
        broadcast({"type": "gm_end"}, keep=False)
    except Exception as e:                  # noqa: BLE001 — 방 전체에 알리고 계속 돈다
        broadcast({"type": "gm_end"}, keep=False)
        broadcast({"type": "notice", "text": f"마스터 오류: {type(e).__name__}: {str(e)[:200]}"})
        print("gm error:", repr(e))
    finally:
        save_state()
        with lock:
            gm_busy = False
        kick_gm()                           # 기다리던 말이 있으면 바로 다음 차례


def do_tool(block):
    args = block.input if isinstance(block.input, dict) else {}
    expr, why = args.get("expr"), args.get("why", "")
    if not isinstance(expr, str) or not isinstance(why, str):
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": json.dumps({"INVALID_JSON": json.dumps(args, ensure_ascii=False)}, ensure_ascii=False)}
    try:
        rolls, total = roll(expr)
    except ValueError as e:
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": str(e)}
    broadcast({"type": "dice", "expr": expr, "rolls": rolls, "total": total, "why": why, "ts": time.time()})
    return {"type": "tool_result", "tool_use_id": block.id,
            "content": json.dumps({"expr": expr, "rolls": rolls, "total": total}, ensure_ascii=False)}


def run_claude():
    import anthropic
    seg = []                                # 주사위 사이 글 한 토막 (기록용)
    json_retries = 0
    while True:
        with lock:
            messages = list(state["messages"])
        try:
            with client.beta.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": EFFORT},
                cache_control={"type": "ephemeral"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                for event in stream:
                    if event.type == "text":
                        seg.append(event.text)
                        broadcast({"type": "gm_delta", "text": event.text}, keep=False)
                response = stream.get_final_message()
            json_retries = 0
        except ValueError:                  # 도구 입력 JSON 을 아예 못 읽음 — 이 차례만 다시
            json_retries += 1
            if json_retries > 2:
                raise
            continue
        except anthropic.RateLimitError:
            broadcast({"type": "notice", "text": "마스터가 숨을 고르는 중 (요청 한도). 잠시 뒤 다시 말해 주세요."})
            break
        except anthropic.APIStatusError as e:
            raise RuntimeError(f"API {e.status_code}: {e.message}") from e

        content = [b.to_dict() for b in response.content]
        with lock:
            state["messages"].append({"role": "assistant", "content": content})

        if response.stop_reason == "refusal":
            broadcast({"type": "notice", "text": "마스터가 이 장면을 진행하지 않았습니다 (안전 정책). 다른 행동을 해 주세요."})
            break
        if response.stop_reason == "pause_turn":
            continue
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break
        if response.stop_reason == "max_tokens":
            raise RuntimeError("도구 입력이 잘림 (max_tokens)")
        log_only({"type": "gm", "text": "".join(seg).strip(), "ts": time.time()})
        seg = []
        results = [do_tool(b) for b in tool_uses]
        with lock:
            state["messages"].append({"role": "user", "content": results})
    log_only({"type": "gm", "text": "".join(seg).strip(), "ts": time.time()})


def run_mock():
    """API 키 없이 화면을 시험할 때. 주사위 하나 굴리고 짧게 답한다."""
    with lock:
        last = state["messages"][-1]["content"]
    rolls, total = roll("d20")
    broadcast({"type": "dice", "expr": "d20", "rolls": rolls, "total": total, "why": "흉내 워든 시험 굴림", "ts": time.time()})
    text = f"(흉내 워든 — API 키가 없어 진짜 Claude 대신 답합니다)\n받은 말:\n{last}\n\nd20 = {total}. 어떻게 할래?"
    for i in range(0, len(text), 6):
        broadcast({"type": "gm_delta", "text": text[i:i + 6]}, keep=False)
        time.sleep(0.03)
    with lock:
        state["messages"].append({"role": "assistant", "content": text})
    log_only({"type": "gm", "text": text, "ts": time.time()})


# ── HTTP ─────────────────────────────────────────────
def clean(s, n):
    return " ".join(str(s or "").split())[:n]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "cairn"

    def log_message(self, fmt, *args):
        if "/api/stream" not in str(args[0] if args else ""):
            super().log_message(fmt, *args)

    def cors(self):
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Token, ngrok-skip-browser-warning")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def reply(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 16 * 1024:
            raise ValueError("too big")
        return json.loads(self.rfile.read(n) or b"{}")

    def me(self):
        with lock:
            return clients.get(self.headers.get("X-Token", ""))

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/play.html"):
            return self.static(ROOT / "play.html", "text/html; charset=utf-8")
        if path == "/health":
            return self.reply(200, {"ok": True, "mock": MOCK})
        if path == "/api/stream":
            return self.stream()
        self.reply(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            data = self.body()
        except (ValueError, json.JSONDecodeError):
            return self.reply(400, {"error": "bad body"})
        if path == "/api/join":
            return self.join(data)
        if path == "/api/send":
            return self.send(data)
        self.reply(404, {"error": "not found"})

    def static(self, file, ctype):
        body = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def join(self, data):
        ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        with lock:
            hits = join_hits.setdefault(ip, deque())
            ok = burst_ok(hits, JOIN_BURST)
        if not ok:
            return self.reply(429, {"error": "입장 시도가 너무 잦습니다. 1분 뒤 다시."})
        if not hmac.compare_digest(str(data.get("password", "")).encode(), PASSWORD.encode()):
            return self.reply(403, {"error": "비밀번호가 틀렸습니다."})
        nick = clean(data.get("nick"), NICK_MAX) or "모험가"
        hue, color = pick_color()
        c = Client(nick, color)
        c.hue = hue
        with lock:
            clients[c.token] = c
        self.reply(200, {"token": c.token, "nick": nick, "color": color})

    def send(self, data):
        c = self.me()
        if not c:
            return self.reply(401, {"error": "다시 입장해 주세요."})
        text = str(data.get("text") or "").strip()[:TEXT_MAX]
        if not text:
            return self.reply(400, {"error": "빈 말"})
        to_gm = bool(data.get("to_gm"))
        if text in ("/새게임", "/reset"):
            with lock:
                state["messages"], state["log"] = [], []
                pending.clear()
            save_state()
            broadcast({"type": "notice", "text": f"{c.nick} 님이 새 게임을 시작했습니다. 워든에게 말을 걸면 캐릭터 만들기부터."})
            return self.reply(200, {"ok": True})
        with lock:
            ok = burst_ok(c.sends, SEND_BURST) and (not to_gm or burst_ok(c.gm_calls, GM_BURST))
        if not ok:
            return self.reply(429, {"error": "너무 빨리 보내고 있습니다."})
        broadcast({"type": "chat", "nick": c.nick, "color": c.color, "text": text, "to_gm": to_gm, "ts": time.time()})
        queue_line(c.nick, text, to_gm)
        self.reply(200, {"ok": True, "gm_busy": gm_busy})

    def stream(self):
        c = self.me()
        if not c:
            return self.reply(401, {"error": "다시 입장해 주세요."})
        self.send_response(200)
        self.cors()
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        with lock:
            fresh = c.online == 0
            c.online += 1
            while not c.q.empty():          # 지난 연결에서 못 받은 것은 hello 기록에 다 있다
                c.q.get_nowait()
            hello = {"type": "hello", "me": {"nick": c.nick, "color": c.color},
                     "log": list(state["log"]), "gm_busy": gm_busy, "mock": MOCK}
        c.push(hello)
        if fresh:
            broadcast({"type": "notice", "text": f"{c.nick} 님이 들어왔습니다."}, keep=False)
            presence()
        try:
            while True:
                try:
                    obj = c.q.get(timeout=HEARTBEAT)
                except queue.Empty:
                    obj = {"type": "ping"}
                line = (json.dumps(obj, ensure_ascii=False) + "\n").encode()
                self.wfile.write(b"%x\r\n%s\r\n" % (len(line), line))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout, OSError):
            pass
        finally:
            with lock:
                c.online -= 1
                gone = c.online == 0
            if gone:
                broadcast({"type": "notice", "text": f"{c.nick} 님이 나갔습니다."}, keep=False)
                presence()


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f"cairn server  http://{HOST}:{PORT}  model={MODEL}  {'MOCK (API 키 없음)' if MOCK else 'Claude API'}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
