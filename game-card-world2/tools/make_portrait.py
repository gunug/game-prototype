"""ComfyUI 로 캐릭터·크리처·장소 포트레이트 생성 — 인스펙터 오른쪽 아래용, 192×256(3:4) 투명 픽셀아트.

768×1024 생성 → 배경 제거 → 대상 크기로 자르기 → 192×256 (3:4, 비율 유지, 빈 곳 투명) → 64색
워크플로우는 같은 폴더의 portrait_workflow.json (API 형식, ComfyUI 에 끌어다 놓으면 열림).

사용법:
  python make_portrait.py --name portrait_knight --label 기사 --kind character --prompt "full body standing pose of ..."
  python make_portrait.py --name portrait_bear --label 곰 --kind creature --prompt "full body of a big wild brown bear standing ..."
기록: ../docs/아이콘_목록.md (make_icon_object.py · make_icon_character.py 와 같은 곳)
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

from icon_common import CHARACTER_PREFIX, OBJECT_PREFIX, fetch_image, record, run_workflow

TOOLS = Path(__file__).resolve().parent
WORKFLOW = TOOLS / "portrait_workflow.json"
PORTRAIT_DIR = TOOLS.parent / "images" / "portrait"
# 파일명 = portrait_<id>. id 는 index.html DEFS 키 그대로 (토끼 = animal)
NAME_RE = re.compile(r"portrait_[a-z0-9]+(?:-[a-z0-9]+)*")
# 캐릭터: 강한 음영 + 흰 배경 (얼굴 초상 때 어두운 갑옷이 검은 배경과 붙어 남았음)
# 크리처: 검은 배경
KINDS = {
    "character": {"subject": "single character", "bg": "white", "shade": True, "body": "full body visible from head to feet"},
    "creature": {"subject": "single creature", "bg": "black", "shade": False, "body": "full body visible"},
    # 장소: 구도는 지정하지 않음 — 세로로 길게 그리라고 하면 잡아늘린 것처럼 나옴 (v0.99.0)
    "place": {"subject": "single place", "bg": "black", "shade": False, "body": "the whole place visible"},
}
# 카드 아이콘(64px) 캐릭터와 같은 음영 문구 — 그림이 카드와 어긋나지 않게
SHADE = ", strong shading with deep defined shadows, high contrast between light and shadow, dramatic directional key light from the upper left, shadowed side of the face clearly darker"
BG_COLORS = {"black": "#000000", "white": "#ffffff white"}
SUFFIX = (
    ", {subject}, centered composition, isolated, {body}, clean readable silhouette, "
    "simple solid {bg} background, no text, no additional objects"
)


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 전신 포트레이트 생성")
    ap.add_argument("--name", required=True, help="파일명 portrait_<카드 id> (확장자 없이)")
    ap.add_argument("--prompt", required=True, help="영문 — 전신 자세·생김새·옷차림")
    ap.add_argument("--kind", choices=sorted(KINDS), required=True, help="character: 흰 배경+강한 음영 / creature: 검은 배경 / place: 세로로 긴 풍경 구도")
    ap.add_argument("--label", default="", help="기록용 한글 이름")
    ap.add_argument("--bg", choices=sorted(BG_COLORS), default=None, help="생성 배경색 (기본: kind 에 따름)")
    ap.add_argument("--seed", type=int, default=None, help="고정 시드 (없으면 랜덤)")
    ap.add_argument("--width", type=int, default=192)     # v0.99.0: 3:4 (128x256 → 192x256)
    ap.add_argument("--height", type=int, default=256)
    ap.add_argument("--colors", type=int, default=64, help="팔레트 색 수 (기본 64)")
    ap.add_argument("--flip", action="store_true", help="결과를 좌우 반전 (왼쪽을 향하게 맞출 때)")
    ap.add_argument("--no-style", action="store_true", help="그림체 머리말을 붙이지 않음")
    ap.add_argument("--force", action="store_true", help="같은 이름 파일이 있으면 덮어씀")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not NAME_RE.fullmatch(a.name):
        sys.exit(f"bad name: {a.name!r} (규칙: portrait_<카드 id>)")
    dest = PORTRAIT_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    kind = KINDS[a.kind]
    bg = a.bg or kind["bg"]
    text = a.prompt.rstrip(" ,.") + (SHADE if kind["shade"] else "") + SUFFIX.format(
        subject=kind["subject"], body=kind["body"], bg=BG_COLORS[bg])
    if not a.no_style:
        text = (OBJECT_PREFIX if a.kind == 'place' else CHARACTER_PREFIX) + text   # 2026-09-21: 장소는 사물용 머리말 (사람이 안 끼게)
    seed = a.seed if a.seed is not None else random.randint(0, 2**48)

    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    wf["pos"]["inputs"]["text"] = text
    wf["sampler"]["inputs"]["seed"] = seed
    wf["resize"]["inputs"].update(width=a.width, height=a.height)
    wf["quant"]["inputs"]["colors"] = a.colors
    wf["save_full"]["inputs"]["filename_prefix"] = f"game-card-world2/{a.name}_full"
    wf["save_portrait"]["inputs"]["filename_prefix"] = f"game-card-world2/{a.name}"

    print(f"seed={seed}")
    outputs = run_workflow(a.url, wf)
    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetch_image(a.url, outputs["save_portrait"]["images"][0]))
    if a.flip:
        from PIL import Image, ImageOps
        ImageOps.mirror(Image.open(dest)).save(dest)

    opts = ["--kind", a.kind]
    if a.flip:
        opts.append("--flip")
    if a.bg and a.bg != kind["bg"]:
        opts += ["--bg", a.bg]
    if a.width != 192 or a.height != 256:
        opts += ["--width", str(a.width), "--height", str(a.height)]
    if a.colors != 64:
        opts += ["--colors", str(a.colors)]
    if a.no_style:
        opts.append("--no-style")
    record(a.name, a.label, a.prompt, seed, opts, file=f"images/portrait/{a.name}.png")

    full = outputs["save_full"]["images"][0]
    print(f"portrait {dest}")
    print(f"full     ComfyUI output/{full['subfolder']}/{full['filename']}")


if __name__ == "__main__":
    main()
