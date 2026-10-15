"""게임 변수 관리 — 워든(LLM)이 대화 맥락에만 기대지 않게, 진행 상황을 서버가 들고 있는다.

워든은 매 차례 맨 앞에 지금 상태(snapshot)를 받아 보고, update_world 도구로 바꾼다.
화면에는 플레이어가 봐도 되는 칸(날짜 · 경계 · 던전 턴 · 보이는 위치 이름)만 나간다.

state["world"] 모양:
    day, watch, turns            1일차 · 아침/오후/밤 · 던전 턴 수
    location                     워든용 위치 (방 번호 써도 됨, 화면엔 안 나감)
    location_public              플레이어에게 보일 위치 이름
    visited                      다녀간 곳 (워든용)
    flags                        시나리오 상태 — FLAGS 의 키만
    notes                        [{id, text}] 워든 메모 (화면엔 안 나감)
"""

WATCHES = ("아침", "오후", "밤")

# 키: (기본값, 설명) — 기본값의 자료형대로 받는다 (숫자 · 참거짓 · 글)
FLAGS = {
    "c3_gas":         ("가득", "C3 튜브웜 둥지의 메탄: 가득 / 폭발 뒤 다시 차는 중 / 분출구 덮음(1d4시간 뒤 숨쉴 만함)"),
    "c4_trap":        ("남음", "C4 종유석 매복: 남음 / 씀"),
    "dam":            ("온전", "C9 댐(진흙 체로 쌓음): 온전 / 손상(1d4분 뒤 터짐) / 무너짐 — 무너지면 C7 나무에 물이 돌아감"),
    "spring_wall":    ("온전", "C8 샘의 진흙 벽: 온전 / 무너짐(C8 · C3 · C2 침수)"),
    "tree":           ("죽어 감", "C7 붉은 은자 나무: 죽어 감 / 물 돌아옴(다시 열매)"),
    "bats":           ("C6", "박쥐 떼 위치: C6 / C7 로 돌아감 — C7 로 가면 루살 은혜"),
    "blood_olms":     (3, "살아 있는 블러드 올름 수 (처음 3)"),
    "blood_olms_awake": (False, "C9 블러드 올름이 깨어 경계 중인가 (C1 로 왔거나 큰 소리면 참)"),
    "geteli":         ("C4 턱 위에 숨음", "게텔리 위치 · 상태"),
    "jhel_fries":     ("C10b 에 숨음", "헬-프리스 위치 · 상태 · 일행에 대한 태도"),
    "mud_sieve":      ("헬-프리스 소지, 충전 1", "진흙 체 소지자 · 남은 충전"),
    "c10a_wall":      ("온전", "C10a 진흙 벽: 온전 / 뚫림"),
    "rusal":          ("C11 우물", "루살 위치 · 일행과의 관계 · 맺은 거래"),
    "boon":           ("안 줌", "루살 은혜: 안 줌 / 받은 사람과 내용"),
    "reward":         ("없음", "결사에 낼 수 있는 성과: 진흙 체 · 구한 조사단원"),
}


def fresh():
    return {"day": 1, "watch": "오후", "turns": 0, "location": "", "location_public": "",
            "visited": [], "flags": {k: v for k, (v, _) in FLAGS.items()}, "notes": [], "next_note": 1}


def ensure(state):
    w = state.setdefault("world", fresh())
    base = fresh()
    for k, v in base.items():
        w.setdefault(k, v)
    for k, (v, _) in FLAGS.items():
        w["flags"].setdefault(k, v)
    return w


def coerce(key, value):
    """도구로 온 값을 그 플래그의 자료형으로."""
    default = FLAGS[key][0]
    if isinstance(default, bool):
        return str(value).strip().lower() in ("true", "1", "참", "예", "yes", "깸", "깨어 있음")
    if isinstance(default, int):
        try:
            return int(float(str(value).strip()))
        except ValueError:
            return default
    return str(value).strip()[:120]


def update(state, args):
    """update_world 도구. 바뀐 것만 받아 고치고, 무엇이 바뀌었는지 글로 돌려준다."""
    w = ensure(state)
    changed = []
    if isinstance(args.get("day"), (int, float)):
        w["day"] = max(1, int(args["day"])); changed.append(f"{w['day']}일차")
    if args.get("watch") in WATCHES:
        w["watch"] = args["watch"]; changed.append(w["watch"])
    if isinstance(args.get("add_turns"), (int, float)) and args["add_turns"]:
        w["turns"] = max(0, w["turns"] + int(args["add_turns"])); changed.append(f"던전 턴 {w['turns']}")
    for k in ("location", "location_public"):
        if isinstance(args.get(k), str) and args[k].strip():
            w[k] = args[k].strip()[:80]; changed.append(f"{k}={w[k]}")
    if isinstance(args.get("location"), str) and args["location"].strip() and w["location"] not in w["visited"]:
        w["visited"].append(w["location"])
    bad = []
    for f in args.get("flags") or []:
        if not isinstance(f, dict) or f.get("key") not in FLAGS:
            bad.append(str(f.get("key") if isinstance(f, dict) else f))
            continue
        w["flags"][f["key"]] = coerce(f["key"], f.get("value", ""))
        changed.append(f"{f['key']}={w['flags'][f['key']]}")
    for text in args.get("add_notes") or []:
        if isinstance(text, str) and text.strip():
            w["notes"].append({"id": w["next_note"], "text": text.strip()[:200]})
            changed.append(f"메모 #{w['next_note']}")
            w["next_note"] += 1
    drop = {int(x) for x in args.get("remove_notes") or [] if str(x).isdigit()}
    if drop:
        w["notes"] = [n for n in w["notes"] if n["id"] not in drop]
        changed.append(f"메모 지움 {sorted(drop)}")
    msg = "바뀜: " + (", ".join(changed) if changed else "없음")
    if bad:
        msg += f" | 없는 플래그 무시: {', '.join(bad)} (쓸 수 있는 것: {', '.join(FLAGS)})"
    return msg


def public(state):
    """화면에 내보내도 되는 것만."""
    w = ensure(state)
    return {"day": w["day"], "watch": w["watch"], "turns": w["turns"], "place": w["location_public"]}


def snapshot(state, chars):
    """워든에게 매 차례 맨 앞에 붙여 줄 지금 상태 (짧은 글)."""
    w = ensure(state)
    lines = [f"[게임 상태 — 서버 기록, 이것이 사실이다. 바꿀 땐 update_world · update_character]",
             f"시간: {w['day']}일차 {w['watch']} · 던전 턴 {w['turns']}",
             f"위치: {w['location'] or '(미정)'} / 플레이어에게 보이는 이름: {w['location_public'] or '(미정)'}",
             f"다녀간 곳: {', '.join(w['visited']) or '없음'}",
             "시나리오 상태:"]
    lines += [f"  {k} = {w['flags'][k]}" for k in FLAGS]
    if w["notes"]:
        lines.append("메모:")
        lines += [f"  #{n['id']} {n['text']}" for n in w["notes"]]
    if chars:
        lines.append("캐릭터:")
        for c in chars:
            st = " ".join(f"{k.upper()} {c.get(k, '?')}/{c.get(k + '_max', '?')}" for k in ("hp", "str", "dex", "wil"))
            items = ", ".join(i["name"] + (f"({i['uses']})" if i.get("uses") else "") for i in c.get("items", []))
            cond = ",".join(c.get("conditions") or [])
            lines.append(f"  {c['name']} [{c.get('player', '')}] {st} 갑옷 {c.get('armor', 0)} gp {c.get('gp', 0)} "
                         f"피로 {c.get('fatigue', 0)} 짐 {c.get('slots_used', 0)}/10 {('상태 ' + cond) if cond else ''}")
            lines.append(f"    소지: {items or '없음'}")
    return "\n".join(lines)


def guide():
    """지시문에 넣을 설명."""
    flag_lines = "\n".join(f"  - {k}: {d}" for k, (_, d) in FLAGS.items())
    return f"""게임 상태 — 서버가 기록한다
- 매 차례 플레이어 말 앞에 [게임 상태] 가 붙어 온다. 기억보다 이것을 믿고 판단한다.
- 시간이 흐르거나(던전 턴 add_turns, 경계 watch, 날짜 day), 위치가 바뀌거나(location 은 워든용 — 방 번호 써도 됨, location_public 은 플레이어에게 보일 이름), 아래 시나리오 상태가 바뀌면 update_world 로 바로 고친다.
- 한 차례에 여러 곳을 지나면 차례가 끝날 때 일행이 서 있는 최종 위치로 location · location_public 을 맞춘다.
- 기억해 둘 사실은 add_notes 로 적고, 끝난 것은 remove_notes 로 지운다.
- 시나리오 상태 키 (flags 에 {{key, value}} 로):
{flag_lines}"""
