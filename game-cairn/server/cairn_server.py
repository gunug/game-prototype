"""Cairn — 플레이 블러드 올름 서버.

LLM 이 워든이 되어 CAS-2 블러드 올름을 진행한다.
두뇌: CAIRN_PROVIDER=openrouter(기본, anthropic/claude-sonnet-5.5 — CAIRN_OR_MODEL 로 바꿈) | claude(claude-opus-5-5)
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
     {"type":"reset"}   /새게임 — 화면 기록을 비운다
     {"type":"image", "url":"/img/..", "name", "caption"}   워든이 그린 정보 수첩 — record_info
- 일행이 새로 알게 된 것(단서 · 들은 이야기 · 읽은 글 · 벽화 · NPC 의 증언 · 지도로 그릴 만한 길)이 생기면 그 장면에서 record_info 로 적는다. 플레이어가 다시 읽는 수첩이다.
- 플레이어가 실제로 보고 들은 것만 적는다. 워든만 아는 진상 · 수치 · 숨은 내용은 적지 않는다. 같은 내용은 두 번 적지 않는다.

처음 알게 된 것 — reveal_lore
- 일행이 아래 것을 처음 눈으로 보거나 마주치거나 이름을 알게 되는 순간, 그 장면을 묘사하면서 reveal_lore 를 부른다. 미리 부르지 않는다.
  blood_olm(블러드 올름) · olm(올름) · tube_worm(튜브웜, 죽은 것이라도) · red_hermit_fruit(붉은 열매 — C1 상자에서 보면) · red_hermit_tree(C7 의 거꾸로 자라는 나무)
  geteli(게텔리를 직접 마주치면) · jhel_fries(헬-프리스를 만나거나 이름을 들으면) · rusal(루살) · faraj_oren(파라즈 · 오렌의 시신을 알아보면) · mud_sieve(진흙 체를 직접 보면)
- 이름을 모르는 괴물이면 처음엔 생김새만 묘사해도 되지만, 그 괴물과 마주친 순간 바로 공개한다 (플레이어 화면에서 이름으로 불린다).

캐릭터 그림
     {"type":"chars", "chars":[...]}   캐릭터 시트 전부 (바뀔 때마다)
     {"type":"chargen", "id"} 기록용 자리 + {"type":"draft", "draft":{...}} 캐릭터 생성 초안 (이름 · 능력치 교환 버튼)
POST /api/consent 헤더 X-Token {"id", "answer": "accept|reject"}   남의 PC 에게 온 요청 — 그 PC 주인만
     {"type":"consent", "id"} 기록 자리 + {"type":"consent_state", "q":{...}}
POST /api/chargen 헤더 X-Token {"id", "action": "name|swap|confirm", "value"}   만든 사람만
     {"type":"info", "entry":{id, kind, title, text, img, when}}   정보 수첩 한 줄 (hello 의 "journal" 에 누적)
     {"type":"world", "world":{day, watch, turns, place}}   게임 상태 중 화면에 보여도 되는 것
     {"type":"reveal", "id", "kind", "title", "words", "desc", "img"}   처음 알게 된 것 (hello 의 "lore" 에 누적)
GET  /lore/<id>   공개된 것의 그림 (공개 전엔 404)
GET  /data/items.json · /images/items/<slug>.jpg   아이템 그림 표 · 그림 (공개)
     {"type":"cost", "kind":"meter|line", "total", "rate", "usd", "label"}   사용료 (달러, rate = 원/달러)
GET  /img/<파일>   그 그림 (server/images/)
GET  /pub/<파일>   플레이어 공개 그림 (docs/images/scenario/ 의 정해 둔 것만)
POST /api/send    헤더 X-Token  {"text", "to_gm"}
GET  /           play.html (이 서버로 바로 들어와도 된다)
GET  /health     {"version" (켤 때의 서버), "page_version" (디스크의 play.html), …}

비밀: server/cairn.pass (입장 비밀번호, 없으면 12341234 로 만든다)
      OPENROUTER_API_KEY 또는 server/openrouter.key  (openrouter)
      ANTHROPIC_API_KEY 또는 server/anthropic.key    (claude)
      환경변수는 Windows 사용자 환경변수(setx)도 직접 읽는다.
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

import chargen
import world

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()   # 서버를 켤 때의 버전


def page_version():
    """디스크의 play.html 버전 — 화면이 낡았는지 알려 주려고."""
    m = re.search(r"const APP_VERSION = '([\d.]+)';", (ROOT / "play.html").read_text(encoding="utf-8"))
    return m.group(1) if m else ""
def _arg(flag, default):
    """--port 8791 --state 경로 — 시험용으로 따로 띄울 때."""
    import sys
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv[:-1] else default


HOST, PORT = "127.0.0.1", int(_arg("--port", os.environ.get("CAIRN_PORT", 8790)))

# 워든 두뇌 — CAIRN_PROVIDER=openrouter(기본) | claude
PROVIDER = os.environ.get("CAIRN_PROVIDER", "openrouter").lower()
OR_MODEL = os.environ.get("CAIRN_OR_MODEL", "anthropic/claude-sonnet-5.5")
AUX_MODEL = os.environ.get("CAIRN_AUX_MODEL", "google/gemini-3.1-flash-lite")   # 보조 작업(수첩 자동 기록) — 싸고 빠른 것
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
IMG_MODEL = os.environ.get("CAIRN_IMG_MODEL", "google/gemini-3.1-flash-lite-image")   # 캐릭터 그림 (OpenRouter)
CLAUDE_MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TOKENS = 16000
MAX_ROUNDS = 30                # 워든 한 차례에 도구 → 이어 말하기 반복 한도

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
OR_KEY_FILE = HERE / "openrouter.key"
STATE_FILE = Path(_arg("--state", HERE / "state.json"))
PUBLIC_IMG = {"/pub/cover.png": "p001_2.png", "/pub/olms.png": "p001.png"}   # 표지 — 플레이어에게 보여도 되는 것만
IMG_DIR = HERE / "images"         # 워든이 그린 그림 (커밋 안 함)

# ── 비밀 ─────────────────────────────────────────────
if not PASS_FILE.exists():
    PASS_FILE.write_text("12341234", encoding="utf-8")
PASSWORD = PASS_FILE.read_text(encoding="utf-8").strip()

def user_env(name):
    """Windows: setx 로 넣은 사용자 환경변수 — 그 전에 뜬 프로세스에서 켜도 읽히게."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except (ImportError, OSError):
        return ""


def secret(env, file):
    return (os.environ.get(env) or user_env(env) or (
        file.read_text(encoding="utf-8").strip() if file.exists() else "")).strip()


if PROVIDER == "claude":
    API_KEY, MODEL = secret("ANTHROPIC_API_KEY", KEY_FILE), CLAUDE_MODEL
else:
    API_KEY, MODEL = secret("OPENROUTER_API_KEY", OR_KEY_FILE), OR_MODEL
MOCK = not API_KEY or os.environ.get("CAIRN_MOCK") == "1"
OR_KEY = secret("OPENROUTER_API_KEY", OR_KEY_FILE)   # 그림은 두뇌와 상관없이 OpenRouter

client = None
if not MOCK and PROVIDER == "claude":
    import anthropic
    client = anthropic.Anthropic(api_key=API_KEY)


# ── 워든 지시문 (한 번 만들고 그대로 — 캐시 접두가 바뀌지 않게) ──
def build_system():
    docs = ROOT / "docs"
    rules = (docs / "룰_요약.md").read_text(encoding="utf-8")
    scen = (docs / "시나리오_블러드올름.md").read_text(encoding="utf-8")
    scen_src = (docs / "src" / "scenario_blood_olms.md").read_text(encoding="utf-8")
    scen_src = re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", scen_src)      # 그림 링크는 뺀다
    rule_src = (docs / "src" / "rule_players_guide.md").read_text(encoding="utf-8")
    chargen = rule_src[rule_src.index("\n## p.8\n"):rule_src.index("\n## p.60\n")]   # 캐릭터 만들기 ~ 배경 20종 표
    chargen = re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", chargen)
    guide = """너는 TRPG Cairn 2e 의 워든(마스터)이다. 모듈 CAS-2 「블러드 올름의 부상」을 진행한다.
여러 플레이어가 한 채팅방에 있다. 플레이어의 말은 `[닉네임] 내용` 꼴로 온다. 같은 차례에 여러 명의 말이 함께 올 수 있다.

진행 원칙
- 한국어로, 짧고 생생하게. 한 번에 6–10문장 안팎. 장면 끝에 무엇을 할지 한 번만 묻는다.
- 같은 내용을 되풀이하지 않는다. 도구를 쓴 일(시트 반영 · 상태 기록 · 위치 갱신 · 시간 경과 · 수첩 기록)은 말하지 않는다 — 화면에 이미 보인다. 괄호로 진행 메모를 붙이지 않는다.
- 냄새 · 소리 · 온도 · 거리 · 위치를 구체적으로. 감정을 대신 말하지 않는다.
- 위험은 미리 분명하게 알린다. 죽음은 경고 없이 오지 않는다.
- 비밀(진상 · 방의 숨은 내용 · NPC 능력치)은 플레이어가 알아낼 때까지 밝히지 않는다.
- 방 번호(C1 · C2 …)와 방 이름표는 워든용 표시라 플레이어에게 말하지 않는다. 보이는 모습으로만 부른다.
- 플레이어가 스스로 정할 일(행동 · 말)을 대신 정하지 않는다. 동료 NPC 는 네가 움직인다.
- 플레이어끼리의 잡담(`(잡담)` 표시)은 맥락으로만 읽고, 따로 답하지 않는다.

주사위
- 결과가 불확실하면 반드시 roll_dice 도구로 굴린다. 결과를 지어내지 않는다.
- 세이브(d20 ≤ 능력치), 피해, 반응(2d6), 운명 주사위(d6), 던전 사건(d6), 캐릭터 생성 모두 도구로.
- 굴린 값과 결과를 서술에 짧게 밝힌다. 예: "DEX 세이브 6 (≤14) 성공".

누가 무엇을 조종하나 — 반드시 지킨다
- 플레이어의 말 앞에 [플레이어 닉 · 캐릭터 이름] 이 붙어 온다. 주어가 없는 말은 그 플레이어 자신의 캐릭터가 하는 행동이다.
- 플레이어는 자기 캐릭터만 움직인다. 다른 캐릭터를 움직이게 할 수 없다.
- 워든도 PC 를 움직이지 않는다. 이번에 플레이어가 선언하지 않은 PC 는 그 자리에서 기다린다 — 따라가거나 줍거나 말하게 하지 않는다. 필요하면 그 플레이어에게 무엇을 할지 묻는다.
  - 다른 플레이어의 PC 에게 무엇을 하게 하는 말(예: "세이블이 문을 열게 한다")은 요청이다. request_consent 를 부르고, 그 PC 는 주인이 수락할 때까지 그 행동을 하지 않는다. 그 답에서는 '요청이 갔다' 고만 말하고, 수락한 것처럼 미리 서술하지 않는다.
  - NPC(동료 NPC 포함)에게 시키는 말도 요청이다. 그 NPC 의 성격 · 특성 · 처지 · 위험을 보고 네가 수락하거나 거부한다. 애매하면 반응 2d6 이나 NPC 의 WIL 세이브를 굴린다. 동료 NPC 는 만든 플레이어(companion_of)의 말을 더 잘 듣지만 무조건 따르지는 않는다.
- 플레이어는 세계를 정의하지 못한다. "문이 열려 있다", "적이 쓰러졌다", "보물이 있다" 처럼 결과 · 사실을 정하는 말은 그 캐릭터가 하려는 '시도' 로만 받아들이고, 결과와 사실은 네가 룰과 시나리오에 따라 정한다.
- 캐릭터가 할 수 없는 일(능력 · 장비 · 위치 밖)은 시도할 수 있는 범위로 줄여 받거나, 왜 안 되는지 짧게 말한다.
- [플레이어 … · 아직 캐릭터 없음] 의 행동 요청은 진행하지 말고 /캐릭터생성 을 권한다.
- [시스템] 이 요청의 수락/거부를 알려 오면 그대로 따른다.

시작
- 캐릭터 만들기는 서버 명령이 한다: 플레이어는 채팅에 /캐릭터생성 , 동료 NPC 는 /동료생성 . 워든은 캐릭터를 직접 굴려 만들지 않는다.
  캐릭터가 없는 플레이어가 말을 걸면 /캐릭터생성 을 쓰라고 짧게 안내한다. 혼자라면 /동료생성 도 권한다.
- 새 캐릭터가 등록되면 [시스템] 이 결과를 보내 준다. 그때는 소개만 한다.
- 파티가 갖춰지면 의뢰를 전하고, 도착 시각과 날씨를 묻고 운명 주사위로 비튼다.

처음 알게 된 것 — reveal_lore
- 일행이 아래 것을 처음 눈으로 보거나 마주치거나 이름을 알게 되는 순간, 그 장면을 묘사하면서 reveal_lore 를 부른다. 미리 부르지 않는다.
  blood_olm(블러드 올름) · olm(올름) · tube_worm(튜브웜, 죽은 것이라도) · red_hermit_fruit(붉은 열매 — C1 상자에서 보면) · red_hermit_tree(C7 의 거꾸로 자라는 나무)
  geteli(게텔리를 직접 마주치면) · jhel_fries(헬-프리스를 만나거나 이름을 들으면) · rusal(루살) · faraj_oren(파라즈 · 오렌의 시신을 알아보면) · mud_sieve(진흙 체를 직접 보면)
- 이름을 모르는 괴물이면 처음엔 생김새만 묘사해도 되지만, 그 괴물과 마주친 순간 바로 공개한다 (플레이어 화면에서 이름으로 불린다).

캐릭터 그림
- 캐릭터 그림은 /캐릭터생성 이 자동으로 그린다. draw_character 는 플레이어가 그림을 다시 그려 달라고 할 때만 부른다.
- prompt 는 영어로: 나이 · 체격 · 피부 · 머리 · 얼굴 · 옷 · 들고 있는 무기와 눈에 띄는 장비 · 배경(직업)의 분위기를 구체적으로. 성별이 정해지지 않았으면 이름과 분위기에 맞게 정해 적는다.
- 그 밖의 때(NPC · 괴물 · 장면)에는 부르지 않는다. 그림이 실패해도 게임을 계속한다.

캐릭터 시트 (화면 옆 시트에 바로 보인다)
- 캐릭터 생성이 끝나면 update_character 로 시트 전체를 등록한다: player · background · age · 능력치(현재와 최대) · hp · armor · gp · items(전부) · traits · bond.
- 진행 중 바뀌면 그때마다 update_character 로 바뀐 것만 보낸다: 피해 · 회복(hp · str · dex · wil), 아이템 얻음(add_items) · 잃음/다 씀(remove_items), 쓰는 횟수(items 의 uses 를 바꿔 add_items 로 같은 이름을 다시 보내면 덮어쓴다), 금화(gp), 피로(fatigue), 상태(conditions: 결핍 · 공포 · 치명 피해 · 사망 등).
- 아이템 칸: 보통 1, petty 0, bulky 2. slots 로 적는다.
- 시트에 이미 보이므로 수치를 글로 길게 되풀이하지 않는다.
"""
    guide += "\n" + world.guide() + "\n"
    return [
        {"type": "text", "text": guide},
        {"type": "text", "text": "## 룰 요약\n\n" + rules},
        {"type": "text", "text": "## 캐릭터 만들기 원문 (Cairn 2e p.8–59, 영문)\n\n" + chargen},
        {"type": "text", "text": "## 시나리오 정리 (워든 전용)\n\n" + scen},
        {"type": "text", "text": "## 시나리오 원문 (워든 전용)\n\n" + scen_src},
    ]


SYSTEM = build_system()

ITEM = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "slots": {"type": "integer", "description": "보통 1, petty 0, bulky 2"},
        "uses": {"type": "string", "description": "남은 횟수나 메모. 예: '3회', 'd6', '1 Armor'"},
    },
    "required": ["name"],
    "additionalProperties": False,
}

LORE_IDS = ["blood_olm", "olm", "tube_worm", "red_hermit_fruit", "red_hermit_tree", "geteli", "jhel_fries", "rusal", "faraj_oren", "mud_sieve"]

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
}, {
    "name": "draw_character",
    "description": "캐릭터 생성이 끝난 캐릭터의 전신 그림을 그려 방에 띄운다. 캐릭터마다 한 번.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "캐릭터 이름"},
            "prompt": {"type": "string", "description": "영어 외모 묘사. 나이 · 성별 · 체격 · 피부 · 머리 · 얼굴 · 옷 · 무기와 장비 · 직업 분위기"},
            "caption": {"type": "string", "description": "그림 밑에 붙일 한국어 한 줄. 예: '아마라 — 궁수, 18세'"},
        },
        "required": ["name", "prompt", "caption"],
        "additionalProperties": False,
    },
}, {
    "name": "reveal_lore",
    "description": "일행이 처음 마주치거나 이름을 알게 된 것을 플레이어 화면에 공개한다 (설명 카드 · 그림 · 키워드 툴팁). 처음 한 번만.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {"id": {"type": "string", "enum": LORE_IDS}},
        "required": ["id"],
        "additionalProperties": False,
    },
}, {
    "name": "record_info",
    "description": "일행이 새로 알게 된 정보(단서 · 들은 이야기 · 읽은 글 · 벽화 · NPC 가 알려 준 사실)를 플레이어 정보 수첩에 적는다. 플레이어가 아는 것만.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "짧은 제목. 예: 올름 굴의 벽화"},
            "text": {"type": "string", "description": "알게 된 내용 2–5문장. 플레이어 눈높이로, 워든 비밀은 빼고"},
        },
        "required": ["title", "text"],
        "additionalProperties": False,
    },
}, {
    "name": "request_consent",
    "description": "다른 플레이어의 PC 에게 무엇을 하게 하자는 요청이 오면 부른다. 그 PC 의 플레이어에게 수락/거부 버튼이 뜬다. NPC 에게는 쓰지 않는다.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "character": {"type": "string", "description": "요청을 받는 PC 이름"},
            "request": {"type": "string", "description": "무엇을 해 달라는지 한 줄"},
            "from_player": {"type": "string", "description": "요청한 플레이어 닉네임"},
        },
        "required": ["character", "request", "from_player"],
        "additionalProperties": False,
    },
}, {
    "name": "update_world",
    "description": "게임 상태(시간 · 던전 턴 · 위치 · 시나리오 상태 · 메모)를 고친다. 바뀐 것만 보낸다.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "day": {"type": "integer"},
            "watch": {"type": "string", "enum": list(world.WATCHES)},
            "add_turns": {"type": "integer", "description": "흐른 던전 턴 수 (보통 1)"},
            "location": {"type": "string", "description": "워든용 위치. 방 번호 써도 됨. 예: C3 튜브웜 둥지 북쪽 출구"},
            "location_public": {"type": "string", "description": "플레이어 화면에 보일 위치 이름. 방 번호 없이. 예: 숨 막히는 넓은 방"},
            "flags": {"type": "array", "description": "바뀐 시나리오 상태",
                      "items": {"type": "object", "properties": {
                          "key": {"type": "string", "enum": list(world.FLAGS)},
                          "value": {"type": "string"}},
                          "required": ["key", "value"], "additionalProperties": False}},
            "add_notes": {"type": "array", "items": {"type": "string"}, "description": "기억해 둘 사실"},
            "remove_notes": {"type": "array", "items": {"type": "integer"}, "description": "지울 메모 번호"},
        },
        "additionalProperties": False,
    },
}, {
    "name": "update_character",
    "description": "캐릭터 시트를 만들거나 고친다. 처음 등록할 땐 hp · str · dex · wil 넷과 items(배경의 시작 장비 전부 — 식량 · 광원 포함)를 빠짐없이. 그 뒤엔 바뀐 칸만. 화면의 시트에 바로 반영된다.",
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "캐릭터 이름 (시트를 찾는 열쇠)"},
            "player": {"type": "string", "description": "조종하는 플레이어 닉네임, 동료 NPC 면 'NPC'"},
            "background": {"type": "string"}, "age": {"type": "integer"},
            "hp": {"type": "integer"}, "hp_max": {"type": "integer"},
            "str": {"type": "integer"}, "str_max": {"type": "integer"},
            "dex": {"type": "integer"}, "dex_max": {"type": "integer"},
            "wil": {"type": "integer"}, "wil_max": {"type": "integer"},
            "armor": {"type": "integer"}, "gp": {"type": "integer"},
            "fatigue": {"type": "integer", "description": "피로 개수 (한 개당 1칸)"},
            "items": {"type": "array", "description": "가진 아이템 전부 — 목록을 통째로 바꾼다",
                      "items": ITEM},
            "add_items": {"type": "array", "description": "얻은 아이템. 같은 이름이 있으면 덮어쓴다",
                          "items": ITEM},
            "remove_items": {"type": "array", "items": {"type": "string"}, "description": "잃거나 다 쓴 아이템 이름"},
            "conditions": {"type": "array", "items": {"type": "string"}, "description": "지금 상태 전부. 예: ['결핍', '공포']. 없으면 []"},
            "traits": {"type": "string", "description": "외모 · 성격 한 줄"},
            "bond": {"type": "string", "description": "본드 한 줄"},
        },
        "required": ["name"],
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
    """방송은 이미 조각(gm_delta)으로 했고, 기록에만 통째로 남긴다. 워든 글이면 이름 나온 것 자동 공개."""
    if obj.get("type") == "gm" and not stale():
        auto_reveal(obj.get("text"))
    if obj.get("text", "").strip():
        with lock:
            state["log"].append(obj)
            del state["log"][:-LOG_KEEP]


def presence():
    with lock:
        users = [{"nick": c.nick, "color": c.color} for c in clients.values() if c.online]
    broadcast({"type": "presence", "users": users}, keep=False)


# ── 상태 저장 ────────────────────────────────────────
state = {"messages": [], "or_messages": [], "log": [], "chars": {}, "revealed": []}
HIST = "messages" if PROVIDER == "claude" else "or_messages"   # 두뇌마다 대화 따로
if STATE_FILE.exists():
    try:
        state.update(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass


world.ensure(state)


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


def pc_of(nick, ko=False):
    """그 플레이어가 조종하는 PC 이름 (없으면 ""). ko=True 면 '이름(한글 표기)'."""
    with lock:
        for c in state["chars"].values():
            if c.get("player") == nick and not any("사망" in x for x in c.get("conditions") or []):
                return f"{c['name']}({c['name_ko']})" if ko and c.get("name_ko") else c["name"]
    return ""


def speaker(nick):
    if nick == "시스템":
        return "[시스템]"
    pc = pc_of(nick, ko=True)
    return f"[플레이어 {nick} · 캐릭터 {pc}]" if pc else f"[플레이어 {nick} · 아직 캐릭터 없음]"


def queue_line(nick, text, to_gm):
    global pending_act
    with lock:
        pending.append(f"{speaker(nick)} {text}" if to_gm else f"(잡담) {speaker(nick)} {text}")
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


# ── 사용료 ───────────────────────────────────────────
KRW = {"rate": float(os.environ.get("CAIRN_KRW", 1400)), "src": "기본값"}
turn_cost = {"usd": 0.0}         # 지금 워든 차례에서 쓴 돈 (그림 포함)
game = {"gen": 0}               # /새게임 마다 +1 — 돌던 워든 차례는 그 자리에서 멈춘다
_turn = threading.local()


def stale():
    return getattr(_turn, "gen", game["gen"]) != game["gen"]


def load_krw():
    """원/달러 환율 — 서버 켤 때 한 번. 실패하면 기본값."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://open.er-api.com/v6/latest/USD", timeout=8) as r:
            d = json.loads(r.read())
        KRW.update(rate=float(d["rates"]["KRW"]), src=d.get("time_last_update_utc", "")[:16])
    except Exception as e:                  # noqa: BLE001
        print("환율 못 받음, 기본값", KRW["rate"], repr(e))


def add_cost(usd, what):
    """쓴 돈을 차례 합계 · 누적에 더하고 머리줄 계기를 갱신한다."""
    usd = float(usd or 0)
    print(f"cost {what} ${usd:.6f}")
    if usd <= 0 or stale():
        return
    with lock:
        turn_cost["usd"] += usd
        state["cost_usd"] = state.get("cost_usd", 0.0) + usd
    broadcast(cost_msg("meter"), keep=False)
    if what == "image":                     # 그림은 바로 그 밑에 한 줄
        broadcast(cost_msg("line", usd, "그림"))


def cost_msg(kind, usd=None, label=""):
    with lock:
        total = state.get("cost_usd", 0.0)
    m = {"type": "cost", "kind": kind, "total": total, "rate": KRW["rate"]}
    if usd is not None:
        m.update(usd=usd, label=label, ts=time.time())
    return m


def extract_info(t0):
    """워든 차례가 끝나면 그 서술에서 '플레이어가 새로 알게 된 것' 만 뽑아 수첩에 — 워든이 record_info 를 잊어도."""
    import urllib.request
    with lock:
        said = "\n".join(e["text"] for e in state["log"] if e.get("type") == "gm" and e.get("ts", 0) >= t0)
        have = [e["title"] for e in state.get("journal", [])]
    if len(said) < 40 or not OR_KEY:
        return
    prompt = ("아래는 TRPG 워든이 플레이어들에게 방금 한 서술이다. 플레이어가 이번에 새로 알게 된 정보만 골라라: "
              "단서 · 이상한 점 · 들은 이야기 · 읽거나 본 글과 그림 · NPC 가 알려 준 사실 · 새로 안 장소나 물건의 생김새.\n"
              "흔한 분위기 묘사 · 행동 결과 · 주사위 · 질문은 빼라. 없으면 빈 배열.\n"
              f"수첩에 이미 있는 제목: {have}\n"
              '답은 JSON 배열만: [{"title": "짧은 제목", "text": "알게 된 내용 1–3문장"}]\n\n서술:\n' + said[:6000])
    body = json.dumps({"model": AUX_MODEL, "max_tokens": 800, "usage": {"include": True},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(OR_URL, body, {"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
                                                "HTTP-Referer": "https://game.onethelab.com", "X-Title": "Cairn Blood Olms"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
        add_cost((d.get("usage") or {}).get("cost"), "chat")
        txt = d["choices"][0]["message"]["content"] or ""
        m = re.search(r"\[.*\]", txt, re.S)
        found = json.loads(m.group(0)) if m else []
    except Exception as e:                  # noqa: BLE001 — 수첩은 덤, 실패해도 게임은 계속
        print("extract_info:", repr(e))
        return
    for f in found[:4]:
        if isinstance(f, dict) and isinstance(f.get("title"), str) and isinstance(f.get("text"), str) and f["text"].strip():
            if not any(h.strip() == f["title"].strip() for h in have):
                add_info("단서", f["title"], f["text"].strip())


def gm_turn(lines):
    global gm_busy
    _turn.gen = game["gen"]
    with lock:
        snap = world.snapshot(state, chars_view())
        state[HIST].append({"role": "user", "content": snap + "\n\n[플레이어]\n" + "\n".join(lines)})
        turn_cost["usd"] = 0.0
        t0 = time.time()
    broadcast({"type": "gm_start"}, keep=False)
    try:
        if MOCK:
            run_mock()
        elif PROVIDER == "claude":
            run_claude()
        else:
            run_openrouter()
        broadcast({"type": "gm_end"}, keep=False)
        if not MOCK and not stale():
            extract_info(t0)
    except Exception as e:                  # noqa: BLE001 — 방 전체에 알리고 계속 돈다
        broadcast({"type": "gm_end"}, keep=False)
        broadcast({"type": "notice", "text": f"마스터 오류: {type(e).__name__}: {str(e)[:200]}"})
        print("gm error:", repr(e))
    finally:
        if turn_cost["usd"] > 0 and not stale():   # 이번 차례 비용 (글 + 그림) — 채팅 끝에
            broadcast(cost_msg("line", turn_cost["usd"], "이번 차례"))
        save_state()
        with lock:
            gm_busy = False
        kick_gm()                           # 기다리던 말이 있으면 바로 다음 차례


def do_tool(block):
    if stale():
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": "새 게임이 시작됨"}
    if block.name == "draw_character":
        return draw_tool(block)
    if block.name == "record_info":
        return info_tool(block)
    if block.name == "request_consent":
        return consent_tool(block)
    if block.name == "update_world":
        with lock:
            msg = world.update(state, block.input if isinstance(block.input, dict) else {})
        broadcast({"type": "world", "world": world.public(state)}, keep=False)
        return {"type": "tool_result", "tool_use_id": block.id, "content": msg}
    if block.name == "reveal_lore":
        return lore_tool(block)
    if block.name == "update_character":
        return sheet_tool(block)
    if block.name != "roll_dice":
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": "없는 도구"}
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



# ── 알게 된 것 (게임 중 공개) ──────────────────────────
# 워든이 reveal_lore 로 부르면 그때부터 플레이어 화면에 툴팁 · 그림이 열린다.
# desc 는 '처음 보고 알 수 있는 것'만 — 숨은 사정(진상 · 능력치 · 약점)은 넣지 않는다.
SCENE = ROOT / "images" / "scene"
LORE = {
    "blood_olm": {"kind": "적", "title": "블러드 올름", "words": ["블러드 올름", "Blood Olm"], "img": SCENE / "blood_olm.jpg",
                  "desc": "사람만 한 허연 동굴 짐승. 눈이 없고, 네 발로 기며 열기를 따라 움직인다. 입가와 가슴이 검붉은 피로 얼룩져 있다."},
    "olm": {"kind": "생물", "title": "올름", "words": ["올름", "Olm"], "img": SCENE / "olm.jpg",
            "desc": "작고 온순해 보이는 눈먼 동굴 생물. 분홍빛 매끈한 피부와 깃털 같은 아가미. 말은 못 하지만 영리해 보인다."},
    "tube_worm": {"kind": "생물", "title": "튜브웜", "words": ["튜브웜", "튜브 웜", "Tube Worm"], "img": SCENE / "tube_worm.jpg",
                  "desc": "개만 한 눈먼 동굴 벌레. 짧고 뭉툭한 다리, 머리에 사슴뿔처럼 갈라진 관이 돋아 있다."},
    "red_hermit_fruit": {"kind": "물건", "title": "붉은 열매", "words": ["붉은 은자 나무 열매", "붉은 은자 나무의 열매", "붉은 은자 열매", "은자 나무 열매", "Red Hermit fruit"], "img": SCENE / "red_hermit_fruit.jpg",
                         "desc": "박처럼 생긴 붉은 열매. 갓 딴 것은 달콤한 향이 나지만, 하루쯤 지나면 갈색으로 물러 썩은 고기 냄새가 난다."},
    "red_hermit_tree": {"kind": "장소", "title": "거꾸로 자라는 나무", "words": ["붉은 은자 나무", "거꾸로 매달린 나무"], "img": SCENE / "c7_atrium.jpg",
                        "desc": "동굴 천장에 뿌리를 박지 않고 거꾸로 매달려 자라는 거대한 나무. 드러난 뿌리가 바닥 쪽으로 늘어져 있다."},
    "geteli": {"kind": "인물", "title": "하이 렉터 게텔리", "words": ["하이 렉터 게텔리", "렉터 게텔리", "게텔리", "Geteli"], "img": SCENE / "geteli.jpg",
               "desc": "조사단을 이끈 학자. 마주친 그는 진흙투성이 옷에 눈이 진홍빛으로 물들어 있다. 제정신으로 보이지 않는다."},
    "jhel_fries": {"kind": "인물", "title": "헬-프리스", "words": ["헬-프리스", "헬프리스", "Jhel-Fries"], "img": SCENE / "jhel_fries.jpg",
                   "desc": "조사단이 동굴 경험을 보고 고용한 현지인. 진흙투성이의 어린 소녀로, 작은 삽을 쥐고 있다."},
    "rusal": {"kind": "인물", "title": "루살", "words": ["루살", "Rusal"], "img": ROOT / "docs" / "images" / "scenario" / "p010.png",
              "desc": "초록 피부의 늙은 물의 정령. 발끝까지 닿는 흰 수염, 흐리지만 날랜 개구리 눈, 물갈퀴 달린 손발."},
    "faraj_oren": {"kind": "인물", "title": "파라즈와 오렌", "words": ["파라즈", "오렌", "Faraj", "Oren"], "img": None,
                   "desc": "조사단원 두 사람. 파라즈는 유물에 밝은 학자, 오렌은 경호를 맡은 숲 안내꾼이었다."},
    "mud_sieve": {"kind": "물건", "title": "진흙 체", "words": ["진흙 체", "Mud Sieve"], "img": SCENE / "mud_sieve.jpg",
                  "desc": "손바닥만 한 초승달 모양 돌. 조사단이 가져간 결사의 유물이다."},
}


NO_AUTO = {"geteli", "mud_sieve"}   # 의뢰서에도 나오는 이름 — 글에 나와도 자동 공개하지 않고 도구로만
_AUTO = sorted(((w, lid) for lid, e in LORE.items() if lid not in NO_AUTO for w in e["words"]), key=lambda x: -len(x[0]))
AUTO_RE = re.compile("|".join(re.escape(w) for w, _ in _AUTO), re.I)
AUTO_ID = {w.lower(): lid for w, lid in _AUTO}



# ── 정보 수첩 — 플레이어가 들어서 아는 것 (다시 읽기용) ──
BRIEF = ("의뢰서 — 사라진 조사단",
         "3주 전 아홉의 결사가 하이 렉터 게텔리가 이끄는 학자 조사단을 실버실크 강을 따라 새로 발견된 동굴로 보냈다. 그 뒤로 소식이 없다.\n"
         "조사단이 가져간 초승달 모양 유물 진흙 체를 무사히 되찾아 오면 1000gp.\n"
         "원래 조사단원 네 명 중 누구든 무사히 데려오면 한 명당 100gp.\n"
         "일행은 강을 따라 내려와 조사단 야영지 바로 서쪽에 닿는다.")


def add_info(kind, title, text, img=None):
    """수첩에 한 줄 — 같은 제목 · 내용이면 다시 넣지 않는다."""
    with lock:
        j = state.setdefault("journal", [])
        if any(e["title"] == title and e["text"] == text for e in j):
            return None
        w = world.public(state)
        e = {"id": len(j) + 1, "kind": kind, "title": clean(title, 60), "text": str(text)[:1200], "img": img,
             "when": f"{w['day']}일차 {w['watch']}" + (f" · {w['place']}" if w.get("place") else ""), "ts": time.time()}
        j.append(e)
    broadcast({"type": "info", "entry": e}, keep=False)
    return e


def info_tool(block):
    args = block.input if isinstance(block.input, dict) else {}
    title, text = args.get("title"), args.get("text")
    if not isinstance(title, str) or not isinstance(text, str) or not text.strip():
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": "title · text 필요"}
    e = add_info("단서", title, text.strip())
    return {"type": "tool_result", "tool_use_id": block.id,
            "content": "정보 수첩에 적었다." if e else "이미 적혀 있다."}


def reveal(lid):
    with lock:
        if lid in state["revealed"]:
            return False
        state["revealed"].append(lid)
    broadcast(dict(lore_view(lid), type="reveal", ts=time.time()))
    v = lore_view(lid)
    add_info(v["kind"], v["title"], v["desc"], v["img"])
    return True


def auto_reveal(text):
    """워든이 글에서 이름을 불렀으면 일행이 알게 된 것 — 긴 이름부터 맞춰 '블러드 올름' 이 '올름' 을 열지 않게."""
    for m in AUTO_RE.finditer(text or ""):
        reveal(AUTO_ID[m.group(0).lower()])


def lore_view(lid):
    e = LORE[lid]
    return {"id": lid, "kind": e["kind"], "title": e["title"], "words": e["words"], "desc": e["desc"],
            "img": f"/lore/{lid}" if e["img"] else None}


def lore_tool(block):
    args = block.input if isinstance(block.input, dict) else {}
    lid = args.get("id")
    if lid not in LORE:
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": f"없는 id. 쓸 수 있는 것: {', '.join(LORE)}"}
    fresh = reveal(lid)
    return {"type": "tool_result", "tool_use_id": block.id,
            "content": f"{LORE[lid]['title']} — 플레이어 화면에 {'공개함' if fresh else '이미 공개돼 있음'}."}

SHEET_INTS = ("age", "hp", "hp_max", "str", "str_max", "dex", "dex_max", "wil", "wil_max", "armor", "gp", "fatigue")
SHEET_STRS = ("player", "background", "traits", "bond")


def item_of(x):
    if not isinstance(x, dict) or not isinstance(x.get("name"), str) or not x["name"].strip():
        return None
    slots = x.get("slots", 1)
    return {"name": clean(x["name"], 40), "slots": max(0, min(4, int(slots))) if isinstance(slots, (int, float)) else 1,
            "uses": clean(x.get("uses", ""), 30), "note": clean(x.get("note", ""), 80)}


def find_char(name):
    key = clean(name, 30)
    for k in state["chars"]:
        if k.lower() == key.lower():
            return k
    return key


def chars_view():
    with lock:
        out = []
        for c in state["chars"].values():
            c = dict(c)
            c["slots_used"] = sum(i["slots"] for i in c.get("items", [])) + int(c.get("fatigue") or 0)
            out.append(c)
    return out


def send_chars():
    broadcast({"type": "chars", "chars": chars_view()}, keep=False)


def sheet_tool(block):
    args = block.input if isinstance(block.input, dict) else {}
    if not isinstance(args.get("name"), str) or not args["name"].strip():
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": json.dumps({"INVALID_JSON": json.dumps(args, ensure_ascii=False)}, ensure_ascii=False)}
    with lock:
        key = find_char(args["name"])
        c = state["chars"].setdefault(key, {"name": key, "items": [], "conditions": []})
        if "image" not in c:                # 먼저 그려 둔 그림이 있으면 붙인다
            for e in reversed(state["log"]):
                if e.get("type") == "image" and e.get("name", "").lower() == key.lower():
                    c["image"] = e["url"]
                    break
        for k in SHEET_INTS:
            if isinstance(args.get(k), (int, float)) and not isinstance(args.get(k), bool):
                c[k] = int(args[k])
        for k in SHEET_STRS:
            if isinstance(args.get(k), str):
                c[k] = clean(args[k], 200)
        for k in ("hp", "str", "dex", "wil"):      # 최대가 없으면 처음 값을 최대로
            if k in c and f"{k}_max" not in c:
                c[f"{k}_max"] = c[k]
        if isinstance(args.get("items"), list):
            c["items"] = [i for i in map(item_of, args["items"]) if i]
        drop = {clean(n, 40).lower() for n in args.get("remove_items") or [] if isinstance(n, str)}
        if drop:
            c["items"] = [i for i in c["items"] if i["name"].lower() not in drop]
        for i in map(item_of, args.get("add_items") or []):
            if i:
                c["items"] = [j for j in c["items"] if j["name"].lower() != i["name"].lower()] + [i]
        if isinstance(args.get("conditions"), list):
            c["conditions"] = [clean(x, 20) for x in args["conditions"] if isinstance(x, str) and x.strip()]
        used = sum(i["slots"] for i in c["items"]) + int(c.get("fatigue") or 0)
    send_chars()
    note = f"{key} 시트 반영. 짐 {used}/10칸."
    if used >= 10:
        note += " 10칸이 찼다 → HP 0 (룰)."
    return {"type": "tool_result", "tool_use_id": block.id, "content": note}



# ── 캐릭터 생성 (/캐릭터생성 · /동료생성) — 절차는 chargen.py, 워든은 소개만 ──
def chargen_view(d):
    v = {k: d.get(k) for k in ("id", "kind", "owner", "owner_color", "status", "name", "name_ko", "names", "names_ko", "background", "intro",
                          "stats", "base", "swap", "hp", "gp", "age", "traits", "bonds", "omen", "rolls", "notes")}
    v["items"] = [{"name": i["name"], "slots": i["slots"], "uses": i["uses"], "note": i.get("note", "")} for i in d["items"]]
    return v


def consent_tool(block):
    """남의 PC 에게 무엇을 하게 하려면 그 플레이어가 수락해야 한다."""
    args = block.input if isinstance(block.input, dict) else {}
    name, req, frm = args.get("character"), args.get("request"), args.get("from_player", "")
    if not isinstance(name, str) or not isinstance(req, str) or not req.strip():
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": "character · request 필요"}
    with lock:
        ch = state["chars"].get(find_char(name))
    if not ch:
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": f"없는 캐릭터: {name}"}
    owner = ch.get("player")
    if owner in (None, "", "NPC"):
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": f"{ch['name']} 은 NPC — 수락 여부는 워든이 그 성격대로 정한다 (필요하면 반응 2d6 · WIL 세이브)."}
    with lock:
        color = next((x.color for x in clients.values() if x.nick == owner), "#888")
        cid = f"q{int(time.time() * 1000) % 10**9}"
        q = {"id": cid, "character": ch["name"], "owner": owner, "owner_color": color,
             "from": clean(frm, NICK_MAX), "request": clean(req, 200), "status": "기다림"}
        state.setdefault("consents", {})[cid] = q
    broadcast({"type": "consent", "id": cid, "ts": time.time()})
    broadcast({"type": "consent_state", "q": q}, keep=False)
    return {"type": "tool_result", "tool_use_id": block.id,
            "content": f"{owner} 님에게 수락/거부 버튼을 띄웠다. 답이 오기 전까지 {ch['name']} 은 그 행동을 하지 않는다. "
                       f"이번 답에서는 요청이 갔다는 것만 알리고 결과를 서술하지 마라."}


def start_chargen(c, kind):
    def roll_cb(expr, why, private=False):
        rolls, total = roll(expr)
        who = c.nick if kind == "pc" else f"{c.nick} 의 동료"
        obj = {"type": "dice", "expr": expr, "rolls": rolls, "total": total, "why": f"{who} · {why}", "ts": time.time()}
        if private:
            c.push(obj)
        else:
            broadcast(obj)
        time.sleep(0.15)                    # 화면에서 하나씩 보이게
        return total

    with lock:
        ages = [x.get("age", 99) for x in state["chars"].values() if x.get("player") not in ("NPC", None)]
    broadcast({"type": "notice", "text": f"{c.nick} 님이 {'캐릭터' if kind == 'pc' else '동료'} 만들기를 시작했습니다. 주사위를 굴립니다…"})
    try:
        d = chargen.create(roll_cb, kind, ages if kind == "pc" else [], c.nick)
    except Exception as e:                  # noqa: BLE001
        broadcast({"type": "notice", "text": f"캐릭터 만들기 실패: {e}"})
        return
    with lock:
        d["id"] = f"d{int(time.time() * 1000) % 10**9}"
        d["status"] = "choosing"
        d["owner_color"] = c.color
        d["owner_token"] = c.token
        state.setdefault("drafts", {})[d["id"]] = d
    if d["omen_private"]:
        c.push({"type": "notice", "text": f"(나만 보는 오멘) {d['omen_private']}"})
    broadcast({"type": "chargen", "id": d["id"], "ts": time.time()})
    broadcast({"type": "draft", "draft": chargen_view(d)}, keep=False)
    save_state()


def finish_chargen(d, owner_nick):
    """확정 → 시트 · 그림 · 워든 소개."""
    player = owner_nick if d["kind"] == "pc" else "NPC"
    sheet = chargen.to_sheet(d, player)
    if d["kind"] == "npc":
        sheet["companion_of"] = owner_nick
    with lock:
        key = find_char(sheet["name"])
        sheet["name"] = key
        state["chars"][key] = sheet
    send_chars()
    try:
        raw, ext, img_cost = draw_image(chargen.image_prompt(d))
        IMG_DIR.mkdir(exist_ok=True)
        fname = f"{int(time.time())}_{secrets.token_hex(3)}.{ext}"
        (IMG_DIR / fname).write_bytes(raw)
        with lock:
            state["chars"][key]["image"] = f"/img/{fname}"
        broadcast({"type": "image", "url": f"/img/{fname}", "name": key,
                   "caption": f"{key} — {d['background']}, {d['age']}세", "ts": time.time()})
        add_cost(img_cost, "image")
        send_chars()
    except Exception as e:                  # noqa: BLE001 — 그림이 안 돼도 캐릭터는 만든다
        broadcast({"type": "notice", "text": f"그림 실패: {str(e)[:150]}"})
    save_state()
    queue_line("시스템", "새 캐릭터가 등록됐다 (굴림 · 시트 · 그림은 서버가 이미 끝냄). "
               "이 캐릭터를 2–4문장으로 생생하게 소개만 하고, 다음 할 일을 짧게 안내하라. 다시 굴리거나 시트를 고치지 마라.\n"
               + chargen.summary_for_warden(d, player), True)


IMG_STYLE = ("Dark fantasy ink-and-wash illustration in the style of an old-school tabletop RPG book, "
             "full body character portrait standing, plain parchment background, muted colors, "
             "no text, no letters, no frame. ")


def draw_image(prompt):
    """OpenRouter 이미지 모델로 한 장. (bytes, 확장자)"""
    import base64
    import urllib.request
    if not OR_KEY:
        raise RuntimeError("OPENROUTER_API_KEY 가 없어 그림을 못 그립니다.")
    body = json.dumps({
        "model": IMG_MODEL, "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": "3:4"},
        "messages": [{"role": "user", "content": IMG_STYLE + prompt}],
    }).encode()
    req = urllib.request.Request(OR_URL, body, {
        "Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
        "HTTP-Referer": "https://game.onethelab.com", "X-Title": "Cairn Blood Olms",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            data = json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenRouter {e.code}: {e.read()[:300].decode('utf-8', 'replace')}") from e
    imgs = ((data.get("choices") or [{}])[0].get("message") or {}).get("images") or []
    if not imgs:
        raise RuntimeError("그림이 오지 않았습니다.")
    head, b64 = imgs[0]["image_url"]["url"].split(",", 1)
    ext = "png" if "png" in head else "webp" if "webp" in head else "jpg"
    return base64.b64decode(b64), ext, (data.get("usage") or {}).get("cost")


def draw_tool(block):
    args = block.input if isinstance(block.input, dict) else {}
    name, prompt = args.get("name"), args.get("prompt")
    if not isinstance(name, str) or not isinstance(prompt, str) or not prompt.strip():
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": json.dumps({"INVALID_JSON": json.dumps(args, ensure_ascii=False)}, ensure_ascii=False)}
    broadcast({"type": "notice", "text": f"워든이 {clean(name, 30)} 의 그림을 그리는 중… (10초 안팎)"}, keep=False)
    try:
        raw, ext, img_cost = draw_image(prompt[:1500])
    except Exception as e:                  # noqa: BLE001 — 그림이 실패해도 게임은 계속
        broadcast({"type": "notice", "text": f"그림 실패: {str(e)[:200]}"})
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True, "content": f"그림 실패: {e}"}
    IMG_DIR.mkdir(exist_ok=True)
    fname = f"{int(time.time())}_{secrets.token_hex(3)}.{ext}"
    (IMG_DIR / fname).write_bytes(raw)
    broadcast({"type": "image", "url": f"/img/{fname}", "name": clean(name, 30),
               "caption": clean(args.get("caption", ""), 120), "ts": time.time()})
    add_cost(img_cost, "image")            # 비용 줄은 그림 밑에
    with lock:
        key = find_char(name)
        if key in state["chars"]:
            state["chars"][key]["image"] = f"/img/{fname}"
    send_chars()
    return {"type": "tool_result", "tool_use_id": block.id, "content": f"{name} 그림을 방에 띄우고 시트에 붙였다."}


def run_claude():
    import anthropic
    seg = []                                # 주사위 사이 글 한 토막 (기록용)
    json_retries = 0
    while True:
        if stale():
            return
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
            u = response.usage
            add_cost(((u.input_tokens or 0) * 4 + (u.cache_creation_input_tokens or 0) * 5
                      + (u.cache_read_input_tokens or 0) * 0.4 + (u.output_tokens or 0) * 20) / 1e6, "chat")
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

        if stale():
            return
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


OR_SYSTEM = "\n\n".join(b["text"] for b in SYSTEM)
# Anthropic 모델은 캐시 지점을 찍어 줘야 지시문(약 3만 토큰)을 싸게 다시 읽는다. Gemini 는 알아서 캐시.
OR_SYSTEM_MSG = ([{"type": "text", "text": OR_SYSTEM, "cache_control": {"type": "ephemeral", "ttl": "1h"}}]   # 쉬었다 와도 1시간은 캐시
                 if OR_MODEL.startswith("anthropic/") else OR_SYSTEM)
def no_addl(s):
    """Gemini 함수 선언은 additionalProperties 를 싫어한다 — 안쪽까지 뺀다."""
    if isinstance(s, dict):
        return {k: no_addl(v) for k, v in s.items() if k != "additionalProperties"}
    if isinstance(s, list):
        return [no_addl(v) for v in s]
    return s


OR_TOOLS = [{"type": "function", "function": {
    "name": t["name"], "description": t["description"], "parameters": no_addl(t["input_schema"]),
}} for t in TOOLS]


def or_stream(messages):
    """OpenRouter chat/completions 스트림(SSE). 글은 흘려 보내고, 끝나면 (글, 도구 호출들, 끝난 이유)."""
    import urllib.request
    if OR_MODEL.startswith("anthropic/"):
        # 이번 차례의 플레이어 말(마지막 user)에도 캐시 지점 — 다음 차례엔 지난 대화까지 캐시로 읽는다
        messages = [dict(m) for m in messages]
        for m in reversed(messages):
            if m.get("role") == "user" and isinstance(m.get("content"), str):
                m["content"] = [{"type": "text", "text": m["content"], "cache_control": {"type": "ephemeral"}}]
                break
    body = json.dumps({
        "model": MODEL, "stream": True, "max_tokens": 4000, "usage": {"include": True},
        "messages": [{"role": "system", "content": OR_SYSTEM_MSG}] + messages,
        "tools": OR_TOOLS,
    }).encode()
    req = urllib.request.Request(OR_URL, body, {
        "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
        "HTTP-Referer": "https://game.onethelab.com", "X-Title": "Cairn Blood Olms",
    })
    text, calls, finish, cost = [], {}, None, 0.0
    try:
        res = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenRouter {e.code}: {e.read()[:300].decode('utf-8', 'replace')}") from e
    with res:
        for raw in res:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue                    # ": OPENROUTER PROCESSING" 같은 주석
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("usage"):
                cost = (chunk["usage"].get("cost") or 0) or cost
                u = chunk["usage"]
                pd = u.get("prompt_tokens_details") or {}
                print(f"usage in={u.get('prompt_tokens')} cache_read={pd.get('cached_tokens')} "
                      f"cache_write={pd.get('cache_write_tokens')} out={u.get('completion_tokens')} ${cost:.4f}", flush=True)
            if chunk.get("error"):
                raise RuntimeError(f"OpenRouter: {chunk['error'].get('message', chunk['error'])}")
            for ch in chunk.get("choices", []):
                d = ch.get("delta") or {}
                if d.get("content"):
                    text.append(d["content"])
                    broadcast({"type": "gm_delta", "text": d["content"]}, keep=False)
                for tc in d.get("tool_calls") or []:
                    c = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "args": ""})
                    c["id"] = tc.get("id") or c["id"]
                    f = tc.get("function") or {}
                    c["name"] = f.get("name") or c["name"]
                    c["args"] += f.get("arguments") or ""
                finish = ch.get("finish_reason") or finish
    add_cost(cost, "chat")
    return "".join(text), [calls[i] for i in sorted(calls)], finish


LEAK_RE = re.compile(r"<ctrl\d+>|^\s*(print\()?default_api\.|(?:^|,)\s*(?:background|name|str_max|hp_max)\s*:", re.M)


def run_openrouter():
    leaks = 0
    for _ in range(MAX_ROUNDS):             # 주사위를 굴리고 이어 말하기
        if stale():
            return
        with lock:
            messages = list(state[HIST])
        text, calls, finish = or_stream(messages)
        if stale():
            return
        if not calls and LEAK_RE.search(text) and leaks < 2:
            # Gemini Flash Lite 가 가끔 도구 호출을 글로 흘린다 (<ctrl46> …). 기록엔 안 남기고 다시 부르게.
            leaks += 1
            broadcast({"type": "gm_retract"}, keep=False)
            broadcast({"type": "notice", "text": "워든이 적던 것을 다시 적는 중…"}, keep=False)
            with lock:
                state[HIST].append({"role": "assistant", "content": "(도구 호출 형식이 깨져 글로 나감)"})
                state[HIST].append({"role": "user", "content": "(시스템) 방금 도구 호출이 글로 새어 나왔다. 글로 쓰지 말고 도구(function call)로 다시 불러라. 값이 많으면 나눠서 여러 번 불러도 된다."})
            continue
        msg = {"role": "assistant", "content": text or None}
        if calls:
            msg["tool_calls"] = [{"id": c["id"] or f"call_{i}", "type": "function",
                                  "function": {"name": c["name"], "arguments": c["args"] or "{}"}}
                                 for i, c in enumerate(calls)]
        with lock:
            state[HIST].append(msg)
        log_only({"type": "gm", "text": text.strip(), "ts": time.time()})
        if not calls:
            if finish == "length":
                broadcast({"type": "notice", "text": "워든의 말이 길어 중간에 끊겼습니다."})
            return
        results = []
        for tc in msg["tool_calls"]:
            try:
                args = json.loads(tc["function"]["arguments"])
            except ValueError:
                args = None
            block = type("B", (), {"id": tc["id"], "name": tc["function"]["name"], "input": args})
            r = do_tool(block)
            results.append({"role": "tool", "tool_call_id": tc["id"], "content": r["content"]})
        with lock:
            state[HIST].extend(results)
    broadcast({"type": "notice", "text": "워든이 주사위를 너무 많이 굴려 이번 차례를 끊었습니다."})


def run_mock():
    """API 키 없이 화면을 시험할 때. 주사위 하나 굴리고 짧게 답한다."""
    with lock:
        last = state[HIST][-1]["content"]
    rolls, total = roll("d20")
    broadcast({"type": "dice", "expr": "d20", "rolls": rolls, "total": total, "why": "흉내 워든 시험 굴림", "ts": time.time()})
    text = f"(흉내 워든 — API 키가 없어 진짜 Claude 대신 답합니다)\n받은 말:\n{last}\n\nd20 = {total}. 어떻게 할래?"
    for i in range(0, len(text), 6):
        broadcast({"type": "gm_delta", "text": text[i:i + 6]}, keep=False)
        time.sleep(0.03)
    with lock:
        state[HIST].append({"role": "assistant", "content": text})
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
            return self.reply(200, {"ok": True, "mock": MOCK, "provider": PROVIDER, "model": MODEL,
                                     "version": VERSION, "page_version": page_version()})
        if path == "/api/stream":
            return self.stream()
        m = re.fullmatch(r"/lore/([a-z_]+)", path)
        if m and m.group(1) in LORE and m.group(1) in state["revealed"] and LORE[m.group(1)]["img"]:
            f = LORE[m.group(1)]["img"]
            return self.static(f, "image/png" if f.suffix == ".png" else "image/jpeg", cors=True)
        if m:
            return self.reply(404, {"error": "아직 공개되지 않음"})
        if path == "/data/item_guide.json":
            return self.static(ROOT / "data" / "item_guide.json", "application/json; charset=utf-8", cors=True)
        if path == "/data/items.json":
            return self.static(ROOT / "data" / "items.json", "application/json; charset=utf-8", cors=True)
        m = re.fullmatch(r"/images/items/([a-z0-9_]+\.jpg)", path)
        if m and (ROOT / "images" / "items" / m.group(1)).exists():
            return self.static(ROOT / "images" / "items" / m.group(1), "image/jpeg", cors=True)
        if path in PUBLIC_IMG:
            return self.static(ROOT / "docs" / "images" / "scenario" / PUBLIC_IMG[path], "image/png", cors=True)
        m = re.fullmatch(r"/img/(\d+_[0-9a-f]{6}\.(png|jpg|webp))", path)
        if m and (IMG_DIR / m.group(1)).exists():
            return self.static(IMG_DIR / m.group(1), "image/" + {"jpg": "jpeg"}.get(m.group(2), m.group(2)), cors=True)
        self.reply(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            data = self.body()
        except (ValueError, json.JSONDecodeError):
            return self.reply(400, {"error": "bad body"})
        if path == "/api/join":
            return self.join(data)
        if path == "/api/consent":
            return self.consent(data)
        if path == "/api/chargen":
            return self.chargen(data)
        if path == "/api/send":
            return self.send(data)
        self.reply(404, {"error": "not found"})

    def static(self, file, ctype, cors=False):
        body = file.read_bytes()
        self.send_response(200)
        if cors:
            self.cors()
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

    def consent(self, data):
        c = self.me()
        if not c:
            return self.reply(401, {"error": "다시 입장해 주세요."})
        with lock:
            q = state.get("consents", {}).get(str(data.get("id")))
        if not q or q["status"] != "기다림":
            return self.reply(404, {"error": "없거나 끝난 요청"})
        if q["owner"] != c.nick:
            return self.reply(403, {"error": f"{q['character']} 의 주인({q['owner']})만 답할 수 있습니다."})
        ok = data.get("answer") == "accept"
        q["status"] = "수락" if ok else "거부"
        broadcast({"type": "consent_state", "q": q}, keep=False)
        save_state()
        queue_line("시스템", f"{q['owner']} 님이 자기 캐릭터 {q['character']} 에 대한 요청 「{q['request']}」(요청: {q['from'] or '?'}) 을 "
                   f"{'수락했다. 이제 그 행동을 서술하라.' if ok else '거부했다. ' + q['character'] + ' 은 그 행동을 하지 않는다.'}", True)
        return self.reply(200, {"ok": True})

    def chargen(self, data):
        c = self.me()
        if not c:
            return self.reply(401, {"error": "다시 입장해 주세요."})
        with lock:
            d = state.get("drafts", {}).get(str(data.get("id")))
        if not d or d["status"] != "choosing":
            return self.reply(404, {"error": "없는 초안"})
        if d["owner"] != c.nick or d["owner_color"] != c.color:
            return self.reply(403, {"error": "만든 사람만 고를 수 있습니다."})
        act, val = data.get("action"), data.get("value")
        if act == "swap":
            if not chargen.apply_swap(d, str(val or "")):
                return self.reply(400, {"error": "잘못된 교환"})
        elif act == "name":
            d["name"] = clean(val, NICK_MAX)
            d["name_ko"] = chargen.NAMES_KO.get(d["name"], "")      # 예시 이름만 — 직접 쓴 이름엔 붙이지 않는다
        elif act == "confirm":
            if not d["name"]:
                return self.reply(400, {"error": "이름을 먼저 정해 주세요."})
            with lock:
                taken = any(k.lower() == d["name"].lower() for k in state["chars"])
            if taken:
                return self.reply(400, {"error": "같은 이름의 캐릭터가 이미 있습니다."})
            d["status"] = "done"
            threading.Thread(target=finish_chargen, args=(d, c.nick), daemon=True).start()
        else:
            return self.reply(400, {"error": "모르는 동작"})
        broadcast({"type": "draft", "draft": chargen_view(d)}, keep=False)
        save_state()
        return self.reply(200, {"ok": True})

    def send(self, data):
        c = self.me()
        if not c:
            return self.reply(401, {"error": "다시 입장해 주세요."})
        text = str(data.get("text") or "").strip()[:TEXT_MAX]
        if not text:
            return self.reply(400, {"error": "빈 말"})
        to_gm = bool(data.get("to_gm"))
        if text in ("/캐릭터생성", "/동료생성"):
            threading.Thread(target=start_chargen, args=(c, "pc" if text == "/캐릭터생성" else "npc"), daemon=True).start()
            return self.reply(200, {"ok": True})
        if text in ("/새게임", "/reset"):
            with lock:
                state["messages"], state["or_messages"], state["log"], state["chars"] = [], [], [], {}
                state["cost_usd"] = 0.0
                state["revealed"] = []
                state["world"] = world.fresh()
                state["drafts"] = {}
                state["consents"] = {}
                state["journal"] = []
                pending.clear()
                game["gen"] += 1
                global pending_act
                pending_act = False
            save_state()
            broadcast({"type": "reset"}, keep=False)
            send_chars()
            broadcast(cost_msg("meter"), keep=False)
            broadcast({"type": "world", "world": world.public(state)}, keep=False)
            add_info("의뢰", *BRIEF)
            broadcast({"type": "notice", "text": f"{c.nick} 님이 새 게임을 시작했습니다. 워든에게 말을 걸면 캐릭터 만들기부터."})
            return self.reply(200, {"ok": True})
        with lock:
            ok = burst_ok(c.sends, SEND_BURST) and (not to_gm or burst_ok(c.gm_calls, GM_BURST))
        if not ok:
            return self.reply(429, {"error": "너무 빨리 보내고 있습니다."})
        broadcast({"type": "chat", "nick": c.nick, "color": c.color, "char": pc_of(c.nick, ko=True), "text": text, "to_gm": to_gm, "ts": time.time()})
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
                     "log": list(state["log"]), "gm_busy": gm_busy, "mock": MOCK, "brain": MODEL,
                     "version": VERSION, "page_version": page_version(),
                     "chars": chars_view(), "cost": cost_msg("meter"),
                     "lore": [lore_view(i) for i in state["revealed"] if i in LORE],
                     "world": world.public(state),
                     "drafts": [chargen_view(d) for d in state.get("drafts", {}).values()],
                     "consents": list(state.get("consents", {}).values()),
                     "journal": state.get("journal", [])}
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
    for c in state["chars"].values():          # 표기가 생기기 전에 만든 시트
        if not c.get("name_ko") and c.get("name") in chargen.NAMES_KO:
            c["name_ko"] = chargen.NAMES_KO[c["name"]]
    if not state.get("journal"):            # 수첩이 없던 게임 — 의뢰서와 이미 알게 된 것부터
        add_info("의뢰", *BRIEF)
        for lid in state.get("revealed", []):
            if lid in LORE:
                v = lore_view(lid)
                add_info(v["kind"], v["title"], v["desc"], v["img"])
        save_state()
    threading.Thread(target=load_krw, daemon=True).start()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f"cairn server v{VERSION}  http://{HOST}:{PORT}  {PROVIDER} · {MODEL}  {'MOCK (API 키 없음)' if MOCK else ''}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
