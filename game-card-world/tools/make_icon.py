"""ComfyUI icon_work_game 워크플로우로 게임 아이콘 생성.

1024 원본 → 배경 제거 → 크롭 → 64px 축소 → 32색 → 투명 PNG.
결과는 game-card-world/images/icon/<name>.png 로 복사한다.

사용법:
  python make_icon.py --name gold_coin --prompt "A polished fantasy game gold coin icon ..."
절차 문서: ../docs/아이콘_생성.md
"""
import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parent.parent / "images" / "icon"
# 파일명 = <분류>_<id>. card 의 id 는 index.html DEFS 키 그대로
CATEGORIES = ("card", "tag", "status", "ui", "fx")
NAME_RE = re.compile(rf"(?:{'|'.join(CATEGORIES)})_[a-z0-9]+(?:-[a-z0-9]+)*")
PROMPT_SUFFIX = (
    ", single object, centered composition, isolated object, clean readable silhouette, "
    "simple solid #000000 background, no text, no characters, no additional objects"
)


def build_prompt(text, name, seed, size, colors):
    sub = f"game-card-world/{name}"
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-9b-int8-ConvRot.safetensors", "weight_dtype": "default"}},
        "lora": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet", 0], "lora_name": "pixel-surgeon-klein-9b.safetensors", "strength_model": 1}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_8b_fp8mixed.safetensors", "type": "flux2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": text}},
        "neg": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["pos", 0]}},
        "latent": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "sampler": {"class_type": "KSampler", "inputs": {
            "model": ["lora", 0], "positive": ["pos", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": seed, "steps": 4, "cfg": 1, "sampler_name": "euler", "scheduler": "simple", "denoise": 1}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["vae", 0]}},
        # 서브그래프: 배경 제거 → 알파 → 크롭 → 축소 → 팔레트 축소
        "bg_model": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}},
        "bg": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["bg_model", 0], "image": ["decode", 0]}},
        "inv": {"class_type": "InvertMask", "inputs": {"mask": ["bg", 0]}},
        "alpha": {"class_type": "JoinImageWithAlpha", "inputs": {"image": ["decode", 0], "alpha": ["inv", 0]}},
        "crop": {"class_type": "ImageCropByMask", "inputs": {"image": ["alpha", 0], "mask": ["bg", 0]}},
        "resize": {"class_type": "ImageResize+", "inputs": {
            "image": ["crop", 0], "width": size, "height": size,
            "interpolation": "area", "method": "pad", "condition": "always", "multiple_of": 0}},
        "split": {"class_type": "SplitImageWithAlpha", "inputs": {"image": ["resize", 0]}},
        "quant": {"class_type": "ImageQuantize", "inputs": {"image": ["split", 0], "colors": colors, "dither": "none"}},
        "join": {"class_type": "JoinImageWithAlpha", "inputs": {"image": ["quant", 0], "alpha": ["split", 1]}},
        "save_full": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": f"{sub}_full"}},
        "save_icon": {"class_type": "SaveImage", "inputs": {"images": ["join", 0], "filename_prefix": sub}},
    }


def api(url, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url + path, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 게임 아이콘 생성")
    ap.add_argument("--name", required=True, help="파일명 (확장자 없이, 영문 소문자·숫자·_·-)")
    ap.add_argument("--prompt", required=True, help="영문 프롬프트")
    ap.add_argument("--seed", type=int, default=None, help="고정 시드 (없으면 랜덤)")
    ap.add_argument("--size", type=int, default=64, help="최종 픽셀 크기 (기본 64)")
    ap.add_argument("--colors", type=int, default=32, help="팔레트 색 수 (기본 32)")
    ap.add_argument("--no-suffix", action="store_true", help="배경 제거용 프롬프트 꼬리말을 붙이지 않음")
    ap.add_argument("--force", action="store_true", help="같은 이름 파일이 있으면 덮어씀")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not NAME_RE.fullmatch(a.name):
        sys.exit(f"bad name: {a.name!r} (규칙: <분류>_<id>, 분류 = {'|'.join(CATEGORIES)}, id = 영문 소문자·숫자·- / docs/아이콘_생성.md)")
    dest = ICON_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    text = a.prompt if a.no_suffix else a.prompt.rstrip(" ,.") + PROMPT_SUFFIX
    seed = a.seed if a.seed is not None else random.randint(0, 2**48)
    prompt = build_prompt(text, a.name, seed, a.size, a.colors)

    try:
        pid = json.loads(api(a.url, "/prompt", {"prompt": prompt}))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit("queue error: " + e.read().decode()[:3000])
    except urllib.error.URLError as e:
        sys.exit(f"ComfyUI 연결 실패 ({a.url}): {e.reason}")
    print(f"queued {pid} seed={seed}")

    t0 = time.time()
    while True:
        hist = json.loads(api(a.url, f"/history/{pid}"))
        if pid in hist:
            break
        if time.time() - t0 > 900:
            sys.exit("timeout (900s)")
        time.sleep(2)

    entry = hist[pid]
    if entry["status"]["status_str"] != "success":
        for kind, msg in entry["status"].get("messages", []):
            if kind == "execution_error":
                print(json.dumps(msg, ensure_ascii=False)[:2000])
        sys.exit("generation failed")

    outputs = entry["outputs"]
    full = outputs["save_full"]["images"][0]
    icon = outputs["save_icon"]["images"][0]
    q = urllib.parse.urlencode({"filename": icon["filename"], "subfolder": icon["subfolder"], "type": icon["type"]})
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(api(a.url, f"/view?{q}"))

    print(f"done {time.time() - t0:.1f}s")
    print(f"icon  {dest}")
    print(f"full  ComfyUI output/{full['subfolder']}/{full['filename']}")


if __name__ == "__main__":
    main()
