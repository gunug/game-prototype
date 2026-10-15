"""data/backgrounds.json · tables.json 을 룰 원문과 대조한다.

    python tools/check_data.py

- 개수: 배경 20 · 이름 · 표 2 × 6행, 특성 8 × 10, 본드 20, 오멘 20
- 아이템 칸은 0 · 1 · 2 만
- 원문 대조: 각 행 · 본드 · 오멘 영어 글의 앞 40자 · 이름 · 특성 낱말이 원문(docs/src/rule_players_guide.md)에 실제로 있는지
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "docs" / "src" / "rule_players_guide.md").read_text(encoding="utf-8")


def norm(s):
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", "", s.lower())


SRCN = norm(SRC)
errors = []


def check_text(where, text, n=40):
    key = norm(text)[:n]
    if key and key not in SRCN:
        errors.append(f"{where}: 원문에 없음 — {text[:70]!r}")


def check_item(where, it):
    for k in ("name_en", "name_ko", "slots"):
        if k not in it:
            errors.append(f"{where}: 아이템에 {k} 없음")
    if it.get("slots") not in (0, 1, 2):
        errors.append(f"{where}: 칸 {it.get('slots')!r}")


bgs = json.loads((ROOT / "data" / "backgrounds.json").read_text(encoding="utf-8"))
if [b["id"] for b in bgs] != list(range(1, 21)):
    errors.append(f"배경 번호: {[b['id'] for b in bgs]}")
for b in bgs:
    w = f"배경 {b['id']} {b['name_en']}"
    check_text(w + " 이름표", b["name_en"], 99)
    for n in b["names"]:
        check_text(f"{w} 이름 {n}", n, 99)
    if len(b["names"]) != 10:
        errors.append(f"{w}: 이름 {len(b['names'])}개")
    check_text(w + " 소개", b["intro_en"])
    for i, it in enumerate(b["gear"]):
        check_item(f"{w} 장비{i}", it)
    if len(b["tables"]) != 2:
        errors.append(f"{w}: 표 {len(b['tables'])}개")
    for ti, tb in enumerate(b["tables"]):
        check_text(f"{w} 표{ti + 1} 질문", tb["question_en"])
        if len(tb["rows"]) != 6:
            errors.append(f"{w} 표{ti + 1}: 행 {len(tb['rows'])}개")
        for ri, r in enumerate(tb["rows"]):
            # 이름+설명 행은 'Name: desc' 로 합쳐 두었으니 콜론을 빼고 비교
            check_text(f"{w} 표{ti + 1} {ri + 1}", r["text_en"].replace(":", " "), 30)
            for ii, it in enumerate(r.get("items") or []):
                check_item(f"{w} 표{ti + 1} {ri + 1} 아이템{ii}", it)
            if not r.get("text_ko"):
                errors.append(f"{w} 표{ti + 1} {ri + 1}: 한글 없음")

tb = json.loads((ROOT / "data" / "tables.json").read_text(encoding="utf-8"))
if len(tb["traits"]) != 8:
    errors.append(f"특성 표 {len(tb['traits'])}개")
for t in tb["traits"]:
    if len(t["rows"]) != 10:
        errors.append(f"특성 {t['key']}: {len(t['rows'])}행")
    for r in t["rows"]:
        check_text(f"특성 {t['key']} {r['en']}", r["en"], 99)
for name, n in (("bonds", 20), ("omens", 20)):
    if [x["n"] for x in tb[name]] != list(range(1, n + 1)):
        errors.append(f"{name} 번호")
    for x in tb[name]:
        check_text(f"{name} {x['n']}", x["text_en"])
        for ii, it in enumerate(x.get("items") or []):
            check_item(f"{name} {x['n']} 아이템{ii}", it)

# 특성 표 순서: 원문 p.10 의 Physique 는 1 Athletic · 6 Scrawny · 10 Towering
ph = next(t for t in tb["traits"] if t["key"] == "physique")["rows"]
if (ph[0]["en"], ph[5]["en"], ph[9]["en"]) != ("Athletic", "Scrawny", "Towering"):
    errors.append(f"체격 표 순서가 원문과 다름: {[r['en'] for r in ph]}")

print("\n".join(errors) if errors else "문제 없음")
print(f"배경 {len(bgs)} · 행 {sum(len(t['rows']) for b in bgs for t in b['tables'])} · 본드 {len(tb['bonds'])} · 오멘 {len(tb['omens'])}")
sys.exit(1 if errors else 0)
