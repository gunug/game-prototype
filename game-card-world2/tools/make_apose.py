"""캐릭터 정면 A포즈 단독 그림 — 나중에 KREA2 Turbo identity edit 의 기준 그림으로 쓴다 (2026-11-06).

KREA 2 Turbo · 집 결(deform — make_scene.py 와 같은 문구) · 정면 · A포즈 · 전신 · 맨손 · 밝은 회색 민무늬 배경.
768×1024 그대로 저장한다 (기준 그림이라 줄이지 않는다) → images/ref/apose_<id>.png

  python tools/make_apose.py                 # 아직 없는 것만
  python tools/make_apose.py --all           # 전부 다시
  python tools/make_apose.py --only knight ally --seed 7

생김새는 roster_characters.py · make_scene.py 의 묘사에서 **손에 든 것 · 등에 멘 것을 뺀** 것 (A포즈는 두 손이 비어야 한다).
기록: ../docs/아이콘_목록.md
"""
import argparse
import random
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from icon_common import fetch_image, record, run_workflow
from make_scene import STYLE, NOT, graph

REF_DIR = Path(__file__).resolve().parent.parent / "images" / "ref"

# (id, 한글 이름, 생김새 — 손에 든 것 없이)
APOSE = [
    ("knight", "가렛", "a young man knight with messy dark brown hair and a gentle face, steel shoulder pauldrons and arm plates "
     "over a brown leather vest, a blue tunic underneath, a plain brown belt, beige trousers, brown leather gloves and boots"),
    ("ally", "세리나", "a cheerful girl of about twelve with dark brown hair under a green hood and short green cloak, bright big eyes, "
     "a brown leather jerkin over a cream shirt, green trousers, brown boots"),
    ("innkeeper", "보른", "a stout middle-aged innkeeper with black hair and a big full black beard, warm eyes, a sage-green apron vest over a rolled-sleeve cream shirt, a brown belt, dark trousers and boots"),
    ("peddler", "오르반", "an old general-goods trader with white hair, a short grey beard and round spectacles, weathered kind face with deep wrinkles, a cream shirt with rolled sleeves under a worn brown leather apron with many small pouches on the belt, dark trousers"),
    ("weaponsmith", "두르간", "a broad weaponsmith with black hair and a thick black mustache, strong forearms, a cream shirt with rolled sleeves under a brown leather apron, dark trousers and boots"),
    ("cook", "올가", "a plump middle-aged woman cook around forty, auburn red hair in a bun under a cream kerchief, rosy round cheeks, small sharp eyes and a grumpy pursed mouth, a yellow blouse, a stained cream apron over a red skirt, dark brown shoes"),
    ("carpenter", "헤이든", "a tall lanky carpenter man around thirty, messy sandy-blond hair, a long narrow face with light stubble, slightly nervous wide eyes, blue work overalls over a white shirt, brown boots"),
    ("armorsmith", "마르그", "a stern older woman armorer in her fifties, dark hair streaked with grey in a tight braid, a sharp hooked nose, thin pressed lips, a cream shirt under a blue vest, a red sash, a brown leather tool apron, heavy dark gloves"),
    ("shieldsmith", "토른", "a big broad-shouldered man in his thirties, short cropped red hair, a square jaw, calm steady eyes, a long pale scar across his left cheek, a blue laced tunic with a brown belt, brown trousers and boots"),
    ("trinketsmith", "네이라", "a young woman bead maker around twenty-five, sleek black hair tied back, narrow sharp eyes, a thin knowing smile, small shell earrings, a cream high-necked knit sweater, a dark skirt"),
    ("herbalist", "실바", "a wary young woman herbalist around twenty-two, pale freckled face, sharp green eyes with a suspicious glare, dark hair under a worn brown hood, a green tunic, a brown satchel strap across the chest, brown boots"),
]
POSE = ("character reference sheet, one single character alone, full body from head to toe, standing straight facing the viewer, "
        "front view, symmetrical A-pose with both arms held down and slightly away from the body, palms open and empty hands, "
        "feet slightly apart, neutral calm expression, whole figure centered with space around it, "
        "plain flat light grey studio background, even soft lighting")
BODY = ("drawn with stylized deformed proportions: a large expressive head, compact sturdy body, small hands and feet")
CHILD = "a small young child, much shorter than an adult, childlike body"
# v2 (2026-11-06): **마네킹 위에 그린다** — 머리 크기 · 키 · 팔 자리를 마네킹이 잡는다 (글로만 그리면 사람마다 머리가 들쭉날쭉했다).
#   마네킹은 apose_mannequin.py — 어른 하나 · 세리나 전용 아이 하나
MANNEQUIN = {"ally": "child"}                       # 나머지는 adult


def upload(url, path):
    import requests
    with open(path, "rb") as f:
        r = requests.post(f"{url}/upload/image", files={"image": (path.name, f, "image/png")}, data={"overwrite": "true"})
    r.raise_for_status()
    return r.json()["name"]


def graph_i2i(text, seed, image_name, denoise, name):
    g = graph(text, seed, 768, 1024, name)
    del g["latent"]
    g["load"] = {"class_type": "LoadImage", "inputs": {"image": image_name}}
    g["enc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["load", 0], "vae": ["vae", 0]}}
    g["ks"]["inputs"]["latent_image"] = ["enc", 0]
    g["ks"]["inputs"]["denoise"] = denoise
    return g


def main():
    ap = argparse.ArgumentParser(description="캐릭터 정면 A포즈 (KREA2)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--denoise", type=float, default=0.7, help="마네킹을 얼마나 덮어 그리나 (낮으면 틀을 더 따른다)")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()
    REF_DIR.mkdir(parents=True, exist_ok=True)
    from apose_mannequin import draw
    mq = {kd: upload(a.url, draw(kd)) for kd in ("adult", "child")}
    for cid, label, desc in APOSE:
        if a.only and cid not in a.only:
            continue
        dest = REF_DIR / f"apose_{cid}.png"
        if dest.exists() and not (a.all or a.only):
            continue
        kd = MANNEQUIN.get(cid, "adult")
        text = f"{POSE}. The character: {desc}" + (f", {CHILD}" if kd == "child" else "") + f". {BODY}. {STYLE}. {NOT}."
        seed = a.seed if a.seed is not None else random.randint(0, 2**31)
        out = run_workflow(a.url, graph_i2i(text, seed, mq[kd], a.denoise, f"apose_{cid}"))
        im = Image.open(BytesIO(fetch_image(a.url, out["save"]["images"][0]))).convert("RGB")
        im.save(dest, optimize=True)
        record(f"apose_{cid}", f"A포즈: {label}", desc, seed, ["(apose-krea2)", "768x1024", f"mannequin {kd}", f"denoise {a.denoise}"], file=f"images/ref/apose_{cid}.png")
        print(f"apose {cid} {label}  {dest}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
