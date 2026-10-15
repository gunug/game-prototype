"""안내 페이지 '아이템' 탭 자료 — data/item_guide.json

    python tools/build_item_guide.py

룰 자료(배경 장비 · 배경 표 · 본드)의 아이템을 이름(slug)으로 모아, 그림 · 칸 · 횟수 · 설명 · 어디서 나오는지를 붙인다.
그림은 tools/item_images.py 가 만든 images/items/<slug>.jpg.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def main():
    bgs = json.loads((ROOT / "data" / "backgrounds.json").read_text(encoding="utf-8"))
    tb = json.loads((ROOT / "data" / "tables.json").read_text(encoding="utf-8"))
    out = {}

    def add(it, kind, where):
        k = slug(it["name_en"])
        e = out.setdefault(k, {"slug": k, "en": it["name_en"], "ko": it["name_ko"], "slots": it.get("slots", 1),
                               "uses": it.get("uses") or "", "note": it.get("note_ko") or "", "kinds": [], "sources": []})
        if not e["note"] and it.get("note_ko"):
            e["note"] = it["note_ko"]
        if kind not in e["kinds"]:
            e["kinds"].append(kind)
        if where not in e["sources"]:
            e["sources"].append(where)

    for b in bgs:
        for it in b["gear"]:
            add(it, "시작 장비", f"{b['name_ko']} 시작 장비")
        for ti, t in enumerate(b["tables"]):
            for ri, r in enumerate(t["rows"]):
                for it in r.get("items") or []:
                    add(it, "배경 표", f"{b['name_ko']} 표{ti + 1}-{ri + 1}")
    for bd in tb["bonds"]:
        for it in bd.get("items") or []:
            add(it, "본드", f"본드 {bd['n']}")
    items = []
    for e in out.values():
        f = ROOT / "images" / "items" / f"{e['slug']}.jpg"
        e["img"] = f"images/items/{e['slug']}.jpg" if f.exists() else ""
        items.append(e)
    items.sort(key=lambda e: e["ko"])
    (ROOT / "data" / "item_guide.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("아이템", len(items), "· 그림 없음", sum(1 for e in items if not e["img"]))


if __name__ == "__main__":
    main()
