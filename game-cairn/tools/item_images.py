"""아이템 그림 한 벌 — 룰 자료(배경 장비 · 배경 표 · 본드)와 시나리오 물건을 Krea2 로.

    python tools/item_images.py            # 없는 것만
    python tools/item_images.py --only rope lantern
    python tools/item_images.py --list     # 목록만

결과: images/items/<slug>.jpg (384px, JPG 85) + data/items.json
      data/items.json = {"<slug>": {"en", "ko", "note_ko", "file"}} — 화면이 이름(영 · 한)으로 그림을 찾는다
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "items"
STYLE = ("A single {thing}, shown as a tabletop RPG inventory item illustration. One object centered on a plain warm parchment "
         "background with a soft shadow, gritty ink lines and muted painted color, old-school fantasy book art. "
         "No people, no hands, no faces. Absolutely no text, no letters, no labels, no captions, no frame.")

# 시나리오(블러드 올름)에서 줍는 물건 — 룰 자료에는 없음
SCENARIO = [
    ("Pickaxe", "곡괭이", "d6", "a sturdy iron pickaxe"),
    ("Pitons", "쇠못", "", "two iron climbing pitons"),
    ("Porcelain Cups", "도자기 잔 세트", "150gp, 깨지기 쉬움", "a set of small delicate antique porcelain cups"),
    ("Blunt Shovel", "무딘 삽", "d6", "an old blunt shovel"),
    ("Small Knife", "작은 칼", "d6", "a small plain knife"),
    ("Blue Moss", "푸른 이끼", "한 줌 10gp", "a handful of vivid blue cave moss"),
    ("Tube Worm Eggs", "튜브웜 알", "", "a clutch of glistening pale egg sacks"),
    ("Sharpened Piton", "갈아 세운 쇠못", "d6", "an iron piton sharpened into a crude dagger"),
    ("Mud Sieve Scroll", "진흙 체 사용법 두루마리", "petty", "a small rolled parchment scroll with three black marks at the bottom"),
    ("Spade", "삽", "d6", "a small digging spade"),
]


# 이름만으론 모호한 것 — 그릴 모습을 따로 적는다
DESC = {
    "rations": "bundle of travel rations: hard bread, dried meat and a wedge of cheese wrapped in cloth and tied with string",
    "lure": "hunting lure: a small scented bait pouch with feathers on a cord",
    "rope": "coil of thick hemp rope",
    "windpipe": "slender wooden pipe flute, the kind that plays a high-pitched note",
    "whistle": "small whistle carved from a gnarled oak branch",
    "oil_can": "small tin oil can with a spout, for refilling a lantern",
    "torch": "unlit wooden torch wrapped in oil-soaked rags",
    "bandages": "roll of linen bandages",
    "repellent": "small stoppered bottle of herbal repellent with a sprig of wolfsbane",
    "soporific_darts": "set of small feathered darts in a leather wrap, their tips dark with sleeping poison",
    "chains": "length of heavy iron chain",
    "chainmail": "shirt of chain mail armor",
    "chain_mail": "shirt of chain mail armor",
    "gem": "single large cut gemstone, cold and brittle",
    "letter": "folded letter sealed with wax",
    "map": "rolled-up hand-drawn map",
    "journal": "old journal bound in bark",
    "costume": "folded theatrical costume with a mask",
    "miracle_oil": "small unlabeled glass bottle of shimmering golden oil",
    "water_shoes": "pair of old leather wading boots with webbed soles",
    "incense": "bundle of incense sticks in a small brass holder, thin smoke rising",
    "metal_arm": "detached mechanical metal prosthetic arm with brass joints",
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def collect():
    bgs = json.loads((ROOT / "data" / "backgrounds.json").read_text(encoding="utf-8"))
    tb = json.loads((ROOT / "data" / "tables.json").read_text(encoding="utf-8"))
    items = []
    for b in bgs:
        items += b["gear"]
        for t in b["tables"]:
            for r in t["rows"]:
                items += r.get("items") or []
    for bd in tb["bonds"]:
        items += bd.get("items") or []
    out = {}
    for i in items:
        k = slug(i["name_en"])
        if k not in out:
            note = i.get("note_en") or ""
            out[k] = {"en": i["name_en"], "ko": i["name_ko"], "note_ko": i.get("note_ko") or "",
                      # 쓰임새 메모를 괄호로 넣으면 그림에 글자로 찍힌다 — 이름만 (모호한 건 DESC)
                      "desc": DESC.get(k) or re.sub(r"\s*\(.*?\)", "", i["name_en"]).strip()}
    for en, ko, note, desc in SCENARIO:
        out.setdefault(slug(en), {"en": en, "ko": ko, "note_ko": note, "desc": desc})
    return out


def main():
    args = sys.argv[1:]
    items = collect()
    if "--list" in args:
        for k, v in items.items():
            print(k, "|", v["ko"], "|", v["desc"][:80])
        print(len(items))
        return
    only = set(args[args.index("--only") + 1:]) if "--only" in args else None
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for i, (k, v) in enumerate(items.items()):
        f = OUT / f"{k}.jpg"
        if (only is None and not f.exists()) or (only and k in only):
            cmd = [sys.executable, str(ROOT / "tools" / "make_image.py"), "--name", f"item_{k}", "--w", "768", "--h", "768",
                   "--seed", str(1000 + i), "--prompt", STYLE.format(thing=v["desc"])]
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=300)
                png = ROOT / "images" / "scene" / f"item_{k}.png"
                im = Image.open(png).convert("RGB")
                im.thumbnail((384, 384))
                im.save(f, quality=85, optimize=True)
                png.unlink()
                print(f"[{i + 1}/{len(items)}] {k}", flush=True)
            except Exception as e:          # noqa: BLE001 — 하나 실패해도 나머지는 계속
                print(f"[{i + 1}/{len(items)}] {k} 실패: {e}", flush=True)
        if f.exists():
            index[k] = {"en": v["en"], "ko": v["ko"], "note_ko": v["note_ko"], "file": f"images/items/{k}.jpg"}
    (ROOT / "data" / "items.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print("그림 있는 아이템", len(index), "/", len(items))


if __name__ == "__main__":
    main()
