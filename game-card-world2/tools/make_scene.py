"""시나리오 카드 그림 생성 — 콜렉터북 📜 흔적의 **시나리오 카드** (큰 그림 한 장 + 짧은 이야기).

배경을 지우지 않는다 (장면 그대로). 768×1024 생성 → 240×320 (3:4) · 64색 → images/scene/<name>.png

사용법:
  python tools/make_scene.py --name scene_goldage --label 금빛 전승 --prompt "a radiant golden city ..."
기록: ../docs/아이콘_목록.md
"""
import argparse
import random
import sys
from pathlib import Path

from PIL import Image

from icon_common import PAINT, build_prompt, fetch_image, record, run_workflow

SCENE_DIR = Path(__file__).resolve().parent.parent / "images" / "scene"
# 옛이야기 책의 한 장 — 장면 전체를 담고, 글자 · 테두리는 넣지 않는다
PREFIX = "Fantasy storybook illustration, a single full scene for a legend, painted like an old fairy-tale page, " + PAINT
SUFFIX = ", the whole scene fills the frame edge to edge, no text, no letters, no ui, no border, no frame, no vignette"


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 시나리오 카드 그림")
    ap.add_argument("--name", required=True, help="파일명 scene_<id>")
    ap.add_argument("--prompt", required=True, help="영문 — 장면")
    ap.add_argument("--label", default="")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--gen-w", type=int, default=768)
    ap.add_argument("--gen-h", type=int, default=1024)
    ap.add_argument("--out-w", type=int, default=240)
    ap.add_argument("--out-h", type=int, default=320)
    ap.add_argument("--colors", type=int, default=64)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not a.name.startswith("scene_"):
        sys.exit(f"bad name: {a.name!r} (규칙: scene_<id>)")
    dest = SCENE_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    seed = a.seed if a.seed is not None else random.randint(0, 2**48)
    # 아이콘 워크플로우를 쓰되 배경 제거 · 크롭 · 축소는 버리고 원본(save_full)만 받는다 (make_bg_tile.py 와 같다)
    prompt = build_prompt(PREFIX + a.prompt.rstrip(" ,.") + SUFFIX, a.name, seed, 64, a.colors)
    prompt["latent"]["inputs"]["width"] = a.gen_w
    prompt["latent"]["inputs"]["height"] = a.gen_h
    for node in ("bg_model", "bg", "inv", "alpha", "crop", "resize", "split", "quant", "join", "save_icon"):
        prompt.pop(node, None)

    print(f"seed={seed}")
    outputs = run_workflow(a.url, prompt)
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    raw = SCENE_DIR / f"{a.name}_full.png"
    raw.write_bytes(fetch_image(a.url, outputs["save_full"]["images"][0]))
    im = Image.open(raw).convert("RGB").resize((a.out_w, a.out_h), Image.LANCZOS)
    im = im.quantize(colors=a.colors, dither=Image.Dither.NONE).convert("RGB")
    im.save(dest)
    raw.unlink()
    record(a.name, a.label, a.prompt, seed, ["(scene)", f"--out-w {a.out_w}", f"--out-h {a.out_h}"], file=f"images/scene/{a.name}.png")
    print(f"scene {dest}  {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
