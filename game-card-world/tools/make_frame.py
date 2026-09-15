"""ComfyUI 로 카드 프레임(카드 한 장 전체 배경) 생성 — 156×212 픽셀아트.

752×1024 생성 → 156×212 축소(area) → 팔레트 축소 → images/frame/<name>.png
워크플로우는 같은 폴더의 card_frame_workflow.json (API 형식, ComfyUI 에 끌어다 놓으면 열림).
가운데는 비워 둔 판 — 카드 내용(아이콘·이름·태그)을 그 위에 얹는다. 모서리 둥글기는 CSS 가 자름.

사용법:
  python make_frame.py --name frame_gold --label 금색 --prompt "warm gold and bronze metal border ..., dark brown center panel"
기록: ../docs/아이콘_목록.md (make_icon.py 와 같은 곳)
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

from make_icon import STYLE_PREFIX, fetch_image, record, run_workflow

TOOLS = Path(__file__).resolve().parent
WORKFLOW = TOOLS / "card_frame_workflow.json"
FRAME_DIR = TOOLS.parent / "images" / "frame"
NAME_RE = re.compile(r"frame_[a-z0-9]+(?:-[a-z0-9]+)*")
# --prompt 에는 테두리 재질·색과 가운데 판 색만 적는다. 틀 모양은 앞뒤로 고정
FRAME_PREFIX = (
    "an inanimate object only, no face, no eyes, no arms, no legs, no people, no creatures: "
    "a flat front-facing blank trading card frame filling the entire image edge to edge, portrait orientation, "
    "orthographic, no perspective, perfectly symmetrical, "
)
FRAME_SUFFIX = (
    ", the border is a thin band about six percent of the card width along all four edges with decorated corners, "
    "a large plain empty smooth center panel taking most of the card, no pattern in the center, "
    "no text, no letters, no numbers, no icons, no characters, nothing in the center"
)


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 카드 프레임 생성")
    ap.add_argument("--name", required=True, help="파일명 frame_<id> (확장자 없이)")
    ap.add_argument("--prompt", required=True, help="영문 — 테두리 재질·색 + 가운데 판 색")
    ap.add_argument("--label", default="", help="기록용 한글 이름")
    ap.add_argument("--seed", type=int, default=None, help="고정 시드 (없으면 랜덤)")
    ap.add_argument("--width", type=int, default=156)
    ap.add_argument("--height", type=int, default=212)
    ap.add_argument("--colors", type=int, default=48, help="팔레트 색 수 (기본 48)")
    ap.add_argument("--no-style", action="store_true", help="그림체 머리말을 붙이지 않음")
    ap.add_argument("--force", action="store_true", help="같은 이름 파일이 있으면 덮어씀")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not NAME_RE.fullmatch(a.name):
        sys.exit(f"bad name: {a.name!r} (규칙: frame_<id>, id = 영문 소문자·숫자·-)")
    dest = FRAME_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    text = FRAME_PREFIX + a.prompt.rstrip(" ,.") + FRAME_SUFFIX
    if not a.no_style:
        text = STYLE_PREFIX + text
    seed = a.seed if a.seed is not None else random.randint(0, 2**48)

    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    wf["pos"]["inputs"]["text"] = text
    wf["sampler"]["inputs"]["seed"] = seed
    wf["resize"]["inputs"].update(width=a.width, height=a.height)
    wf["quant"]["inputs"]["colors"] = a.colors
    wf["save_full"]["inputs"]["filename_prefix"] = f"game-card-world/{a.name}_full"
    wf["save_frame"]["inputs"]["filename_prefix"] = f"game-card-world/{a.name}"

    print(f"seed={seed}")
    outputs = run_workflow(a.url, wf)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetch_image(a.url, outputs["save_frame"]["images"][0]))

    opts = []
    if a.width != 156 or a.height != 212:
        opts += ["--width", str(a.width), "--height", str(a.height)]
    if a.colors != 48:
        opts += ["--colors", str(a.colors)]
    if a.no_style:
        opts.append("--no-style")
    record(a.name, a.label, a.prompt, seed, opts, file=f"images/frame/{a.name}.png")

    full = outputs["save_full"]["images"][0]
    print(f"frame {dest}")
    print(f"full  ComfyUI output/{full['subfolder']}/{full['filename']}")


if __name__ == "__main__":
    main()
