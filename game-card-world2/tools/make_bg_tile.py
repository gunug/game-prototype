"""원정 트랙 배경 타일 생성 — 가로로 이어 붙여 깔 그림 (땅마다 하나).

아이콘과 다른 점: **배경을 지우지 않고 자르지도 않는다**. 대신 좌우가 이어지도록 이음매를 섞어
(가로 타일링 가능) 칸 너비의 배수로 줄여 저장한다. 결과는 game-card-world2/images/bg/<name>.png.

사용법:
  python tools/make_bg_tile.py --name bg_mountain --label 산 --prompt "a rocky mountain slope with scree and pine"
옵션: --kan 3 (몇 칸 폭) · --out-w · --out-h · --colors · --seed · --force · --no-seam (이음매 안 섞음)
"""
import argparse
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from icon_common import PAINT, build_prompt, fetch_image, record, run_workflow

BG_DIR = Path(__file__).resolve().parent.parent / "images" / "bg"
# 배경 · 풍경 — 사람도 글자도 끼지 않게, 가로로 이어 붙일 그림이라고 못 박음
SCENE_PREFIX = (
    "Side-scrolling game background strip, horizontally tileable seamless landscape band, "
    "wide panoramic view, flat side-on camera, " + PAINT
)
SCENE_SUFFIX = (
    ", empty landscape only, no person, no human, no creature, no animal, no text, no ui, "
    "no vignette, no border, no frame, even lighting across the whole width"
)


def quiet_roll(im, band):
    """이음매를 **한산한 자리**로 옮긴다.
    섞는 자리는 두 군데 — 끝(x≈0)과 반 폭 건너(x≈W/2) — 이 둘이 함께 한산한 곳을 고른다.
    타일은 얼마를 굴려도 그대로 이어지므로, 굴려서 나무·바위를 이음매에서 비켜 놓는다."""
    a = np.asarray(im.convert("L"), dtype=float)
    H, W = a.shape
    col = np.zeros(W)
    col[: W - 1] = np.abs(np.diff(a, axis=1)).mean(0)               # 세로선마다 가로 변화량 = 북적임
    col[W - 1] = col[W - 2]
    w = max(4, int(W * band))
    k = np.ones(w) / w
    sm = np.convolve(np.tile(col, 3), k, "same")[W : 2 * W]         # 섞는 폭만큼 뭉갬 (둘레로 이어서)
    q = int(np.argmin(sm + np.roll(sm, -(W // 2))))                 # 두 자리가 함께 한산한 곳
    out = Image.new(im.mode, (W, H))
    out.paste(im.crop((q, 0, W, H)), (0, 0))
    out.paste(im.crop((0, 0, q, H)), (W - q, 0))
    return out, q


def tone_match(im, k=10):
    """양 끝의 **밝기·색을 맞춘다** — 왼쪽 끝과 오른쪽 끝의 차이를 가로로 고르게 나눠 없앤다.
    이걸 안 하면 이음매를 섞을 때 두 하늘의 톤이 달라 네모난 자국이 남는다."""
    a = np.asarray(im, dtype=float)
    H, W = a.shape[:2]
    d = a[:, :k].mean(1) - a[:, W - k :].mean(1)                    # 줄마다 (왼끝 − 오른끝)
    t = np.linspace(-0.5, 0.5, W)[None, :, None]
    return Image.fromarray(np.clip(a + d[:, None, :] * t, 0, 255).astype("uint8"), im.mode)


def seamless(im, band=0.16):
    """좌우가 이어지게 — 반 폭 굴린 그림을 양 끝에서 겹쳐 섞는다.
    끝(x=0)은 굴린 그림의 값(원본 W/2)이라 되풀이해도 끊기지 않는다. 가운데는 원본 그대로."""
    W, H = im.size
    rolled = Image.new(im.mode, (W, H))
    rolled.paste(im.crop((W // 2, 0, W, H)), (0, 0))
    rolled.paste(im.crop((0, 0, W // 2, H)), (W - W // 2, 0))
    mask = Image.new("L", (W, 1))
    px = mask.load()
    for x in range(W):
        d = abs(x - (W - 1) / 2) / ((W - 1) / 2)                   # 가운데 0 → 끝 1
        t = max(0.0, (d - (1 - band)) / band)
        px[x, 0] = int(round(255 * (t * t * (3 - 2 * t))))          # 매끄러운 계단
    return Image.composite(rolled, im, mask.resize((W, H)))


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 원정 배경 타일 생성")
    ap.add_argument("--name", required=True, help="파일명 (bg_<id>)")
    ap.add_argument("--prompt", required=True, help="영문 프롬프트 (풍경만)")
    ap.add_argument("--label", default="", help="기록용 한글 이름")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--kan", type=int, default=3, help="타일이 몇 칸 폭인지 (기록용, 기본 3)")
    ap.add_argument("--gen-w", type=int, default=1024)
    ap.add_argument("--gen-h", type=int, default=448)
    ap.add_argument("--out-w", type=int, default=288, help="저장 폭 (기본 288 = 96px 칸 셋)")
    ap.add_argument("--out-h", type=int, default=126, help="저장 높이 (기본 126 = 트랙 높이)")
    ap.add_argument("--colors", type=int, default=32)
    ap.add_argument("--band", type=float, default=0.16, help="이음매를 섞는 폭 (0~1, 기본 0.16). 넓으면 겹친 그림이 비쳐 보인다")
    ap.add_argument("--no-tone", action="store_true", help="양 끝 톤 맞추기 생략")
    ap.add_argument("--no-pick", action="store_true", help="이음매 자리 고르기 생략 (그림 그대로의 끝을 씀)")
    ap.add_argument("--no-seam", action="store_true", help="이음매 섞기 생략")
    ap.add_argument("--no-style", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not a.name.startswith("bg_"):
        sys.exit(f"bad name: {a.name!r} (규칙: bg_<id>)")
    dest = BG_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    text = a.prompt.rstrip(" ,.") + SCENE_SUFFIX
    if not a.no_style:
        text = SCENE_PREFIX + text
    seed = a.seed if a.seed is not None else random.randint(0, 2**48)
    # 아이콘 워크플로우를 쓰되 **배경 제거·크롭·축소는 버리고** 원본(save_full)만 받는다
    prompt = build_prompt(text, a.name, seed, 64, a.colors)
    prompt["latent"]["inputs"]["width"] = a.gen_w
    prompt["latent"]["inputs"]["height"] = a.gen_h
    for node in ("bg_model", "bg", "inv", "alpha", "crop", "resize", "split", "quant", "join", "save_icon"):
        prompt.pop(node, None)

    print(f"seed={seed}")
    outputs = run_workflow(a.url, prompt)
    full = outputs["save_full"]["images"][0]
    raw = BG_DIR / f"{a.name}_full.png"
    BG_DIR.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(fetch_image(a.url, full))

    im = Image.open(raw).convert("RGB")
    if not a.no_seam:
        if not a.no_pick:
            im, q = quiet_roll(im, a.band)
            print(f"이음매 자리 {q}/{im.size[0]}")
        if not a.no_tone:
            im = tone_match(im)
        im = seamless(im, a.band)
    im = im.resize((a.out_w, a.out_h), Image.LANCZOS).quantize(colors=a.colors, dither=Image.Dither.NONE).convert("RGB")
    im.save(dest)
    raw.unlink()

    opts = [f"--kan {a.kan}", f"--out-w {a.out_w}", f"--out-h {a.out_h}", f"--band {a.band}"]
    if a.no_seam:
        opts.append("--no-seam")
    if a.no_pick:
        opts.append("--no-pick")
    if a.no_tone:
        opts.append("--no-tone")
    record(a.name, a.label, a.prompt, seed, ["(bg-tile)"] + opts, file=f"images/bg/{a.name}.png")
    print(f"tile  {dest}  {a.out_w}x{a.out_h}  ({a.kan}칸)")


if __name__ == "__main__":
    main()
