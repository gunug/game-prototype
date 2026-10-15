"""캐릭터 생성 — 룰 절차를 프로그램이 그대로 밟는다 (Cairn 2e p.8–17).

배경 d20 → 배경 표 d6 ×2 → STR · DEX · WIL 3d6 → HP d6 (+배경 보너스) → 금화 3d6 (+표 · 본드)
→ 특성 d10 ×8 → 본드 d20 (밭지기는 두 번) → 나이 2d20+10 → 가장 어린 PC 면 오멘 d20 (주워진 아이는 따로, 혼자만 봄)

자료: game-cairn/data/backgrounds.json · tables.json (룰 원문에서 정리, scripts 로 검증)
굴림은 roll(expr, why, private) 콜백으로 — 서버가 방에 보여 준다.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
_bg = _tables = None
NAMES_KO = json.loads((DATA / "names_ko.json").read_text(encoding="utf-8"))   # 배경 예시 이름 → 한국식 표기


def data():
    global _bg, _tables
    if _bg is None:
        _bg = {b["id"]: b for b in json.loads((DATA / "backgrounds.json").read_text(encoding="utf-8"))}
        _tables = json.loads((DATA / "tables.json").read_text(encoding="utf-8"))
    return _bg, _tables


def sheet_item(it):
    """자료의 ITEM → 시트 아이템."""
    note = it.get("note_ko") or ""
    return {"name": it["name_ko"], "slots": int(it.get("slots", 1)), "uses": it.get("uses") or "",
            "note": note, "en": it.get("name_en", "")}


def create(roll, kind, existing_ages, owner):
    """초안 하나. roll(expr, why, private=False) -> total.
    kind: 'pc' | 'npc'. existing_ages: 이미 있는 PC 나이들 (가장 어린지 보려고)."""
    bgs, tb = data()
    d = {"kind": kind, "owner": owner, "notes": [], "items": [], "rolls": []}
    b = bgs[roll("d20", "배경")]
    d["bg_id"] = b["id"]
    d["background"] = b["name_ko"]
    d["background_en"] = b["name_en"]
    d["names"] = b["names"]
    d["names_ko"] = {n: NAMES_KO.get(n, "") for n in b["names"]}
    d["intro"] = b["intro_ko"]
    d["items"] += [sheet_item(i) for i in b["gear"]]
    gp_bonus = 0
    hp_bonus = []
    extra_rules = [b.get("special_en") or ""]
    for t in b["tables"]:
        r = t["rows"][roll("d6", t["question_ko"]) - 1]
        d["rolls"].append({"q": t["question_ko"], "a": r["text_ko"]})
        d["items"] += [sheet_item(i) for i in r.get("items") or []]
        gp_bonus += int(r.get("gp") or 0)
        if r.get("hp_bonus"):
            hp_bonus.append(r["hp_bonus"])
        if r.get("note_ko"):
            d["notes"].append(r["note_ko"])
        extra_rules.append(r.get("text_en") or "")      # 표 결과가 오멘 · 본드를 더 굴리라고 하면
    if b.get("special_ko"):
        d["notes"].append(b["special_ko"])

    d["base"] = {k: roll("3d6", k.upper()) for k in ("str", "dex", "wil")}
    d["stats"] = dict(d["base"])
    d["swap"] = ""
    d["hp"] = roll("d6", "HP") + sum(roll(h, "HP 보너스") for h in hp_bonus)
    d["gp"] = roll("3d6", "금화") + gp_bonus

    d["traits"] = []
    for tr in tb["traits"]:
        row = tr["rows"][roll("d10", tr["name_ko"]) - 1]
        d["traits"].append({"key": tr["key"], "name": tr["name_ko"], "ko": row["ko"], "en": row["en"]})

    d["bonds"] = []
    rules = " ".join(extra_rules)
    n_bonds = 2 if re.search(r"second time on the Bonds", rules, re.I) else 1
    for i in range(n_bonds):
        bond = tb["bonds"][roll("d20", "본드" if i == 0 else "두 번째 본드") - 1]
        d["bonds"].append(bond["text_ko"])
        d["items"] += [sheet_item(x) for x in bond.get("items") or []]
        d["gp"] += int(bond.get("gp") or 0)
        if bond.get("note_ko"):
            d["notes"].append(bond["note_ko"])

    d["age"] = roll("2d20+10", "나이")
    d["omen"] = ""
    d["omen_private"] = ""
    if re.search(r"roll on the Omens", rules, re.I):                  # 주워진 아이 · 약장수 가짜 예언 — 따로 굴려 혼자만 본다
        d["omen_private"] = tb["omens"][roll("d20", "오멘 (본인만 봄)", True) - 1]["text_ko"]
    if kind == "pc" and all(d["age"] < a for a in existing_ages):
        d["omen"] = tb["omens"][roll("d20", "오멘 (가장 어린 PC)") - 1]["text_ko"]
    d["name"] = ""
    d["name_ko"] = ""
    return d


SWAPS = {"": None, "str-dex": ("str", "dex"), "str-wil": ("str", "wil"), "dex-wil": ("dex", "wil")}


def apply_swap(d, key):
    if key not in SWAPS:
        return False
    d["stats"] = dict(d["base"])
    pair = SWAPS[key]
    if pair:
        a, b = pair
        d["stats"][a], d["stats"][b] = d["base"][b], d["base"][a]
    d["swap"] = key
    return True


def to_sheet(d, player):
    s = d["stats"]
    traits = " · ".join(f"{t['name']} {t['ko']}" for t in d["traits"])
    return {
        "name": d["name"], "name_ko": d.get("name_ko", ""), "player": player, "background": d["background"], "age": d["age"],
        "hp": d["hp"], "hp_max": d["hp"], "str": s["str"], "str_max": s["str"],
        "dex": s["dex"], "dex_max": s["dex"], "wil": s["wil"], "wil_max": s["wil"],
        "armor": 0, "gp": d["gp"], "fatigue": 0, "conditions": [],
        "items": d["items"], "traits": traits, "bond": " / ".join(d["bonds"]),
        "notes": d["notes"] + ([f"오멘: {d['omen']}"] if d["omen"] else []),
    }


def image_prompt(d):
    t = {x["key"]: x["en"] for x in d["traits"]}
    gear = ", ".join(i["en"] for i in d["items"] if i.get("en") and i["slots"] > 0)[:300]
    return (f"Full body portrait of {d['name'] or 'an adventurer'}, a {d['age']}-year-old {t.get('physique', '').lower()} "
            f"{d['background_en'].lower()} adventurer, {t.get('skin', '').lower()} skin, {t.get('hair', '').lower()} hair, "
            f"{t.get('face', '').lower()} face, wearing {t.get('clothing', '').lower()} clothes, "
            f"a {t.get('virtue', '').lower()} yet {t.get('vice', '').lower()} look. Carrying: {gear}.")


def summary_for_warden(d, player):
    s = d["stats"]
    lines = [f"{d['name']}{'(' + d['name_ko'] + ')' if d.get('name_ko') else ''} — {d['background']} ({d['background_en']}), {d['age']}세, 플레이어 {player}",
             f"STR {s['str']} DEX {s['dex']} WIL {s['wil']} HP {d['hp']} 금화 {d['gp']}",
             "특성: " + " · ".join(f"{t['name']} {t['ko']}" for t in d["traits"]),
             "배경 표: " + " / ".join(f"{r['q']} → {r['a']}" for r in d["rolls"]),
             "본드: " + " / ".join(d["bonds"])]
    if d["omen"]:
        lines.append("오멘(모두에게 읽어 줌): " + d["omen"])
    if d["notes"]:
        lines.append("특이사항: " + " / ".join(d["notes"]))
    return "\n".join(lines)
