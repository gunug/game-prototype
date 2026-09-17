"""ComfyUI icon_work_game 워크플로우로 게임 아이콘 생성.

1024 원본 → 배경 제거 → 크롭 → 64px 축소 → 32색 → 투명 PNG.
결과는 game-card-world2/images/icon/<name>.png 로 복사한다.

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
# 파일명·프롬프트 기록 — 생성에 성공할 때마다 갱신 (같은 파일명은 덮어씀, 이전 기록은 git)
LOG_MD = Path(__file__).resolve().parent.parent / "docs" / "아이콘_목록.md"
LOG_HEAD = (
    "# 아이콘 목록\n\n"
    "> 이미지 파일명과 생성에 쓴 프롬프트 기록 (아이콘·카드 프레임). `tools/make_icon.py`·`tools/make_frame.py` 가 생성에 성공할 때마다 자동으로 갱신한다.\n"
    "> 같은 파일명은 덮어쓴다 (이전 기록은 git). `- 메모:` 줄은 다시 뽑아도 남는다.\n"
    "> 다시 뽑기: `python tools/make_icon.py --name <파일명> --seed <seed> <옵션> --prompt \"<프롬프트>\"`\n"
    "> 규칙·요령은 `아이콘_프롬프트.md`.\n"
)
# 파일명 = <분류>_<id>. card 의 id 는 index.html DEFS 키 그대로
CATEGORIES = ("card", "tag", "status", "ui", "fx")
NAME_RE = re.compile(rf"(?:{'|'.join(CATEGORIES)})_[a-z0-9]+(?:-[a-z0-9]+)*")
# 그림체 통일 — 모든 아이콘 앞에 붙임. 밝은 분위기, 어린이용 아님, 실사 아님
# 작게 보여도 읽히도록 슈퍼 데포르메 비율 (단순화 버전은 단조로워서 폐기)
STYLE_PREFIX = (
    "Stylized fantasy RPG game icon, super deformed (SD) style with chunky exaggerated proportions, "
    "characters have an oversized head and a small compact body, "
    "hand-painted semi-realistic illustration style, bold readable shapes with clean dark outlines, "
    "painterly brush texture, soft cel-shaded volumes, "
    "bright warm lighting, rich vivid colors, grounded mature art direction for teen and adult players. "
)
PROMPT_SUFFIX = (
    ", single object, centered composition, isolated object, clean readable silhouette, "
    "simple solid {bg} background, no text, no characters, no additional objects"
)
# 검은 오브젝트·불·고리 모양은 검은 배경이 남으므로 흰 배경으로
BG_COLORS = {"black": "#000000", "white": "#ffffff white"}


def build_prompt(text, name, seed, size, colors):
    sub = f"game-card-world2/{name}"
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


def record(name, label, prompt, seed, opts, file=None):
    """이미지 목록 md 에 파일명별 기록 갱신. file 기본은 images/icon/<name>.png (make_frame.py 도 씀)"""
    file = file or f"images/icon/{name}.png"
    text = LOG_MD.read_text(encoding="utf-8") if LOG_MD.exists() else LOG_HEAD
    m = re.search(rf"<!-- icon:{re.escape(name)} -->\n(.*?)<!-- /icon -->\n?", text, re.S)
    old = m.group(1) if m else ""
    if not label:
        h = re.match(rf"### {re.escape(name)} — (.+)", old)
        label = h.group(1) if h else ""
    memos = [line for line in old.splitlines() if line.startswith("- 메모:")]
    body = "\n".join([
        f"### {name}" + (f" — {label}" if label else ""),
        f"- 파일: `{file}`",
        f"- 생성: {time.strftime('%Y-%m-%d')} · seed `{seed}` · 옵션 " + (f"`{' '.join(opts)}`" if opts else "기본"),
        *memos,
        "```", prompt, "```", "",
    ])
    section = f"<!-- icon:{name} -->\n{body}<!-- /icon -->\n"
    text = text[:m.start()] + section + text[m.end():] if m else text.rstrip("\n") + "\n\n" + section
    LOG_MD.write_text(text, encoding="utf-8", newline="\n")


def api(url, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url + path, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def run_workflow(url, prompt, timeout=900):
    """API 형식 워크플로우를 큐에 넣고 끝날 때까지 기다림 → outputs. 실패하면 종료"""
    try:
        pid = json.loads(api(url, "/prompt", {"prompt": prompt}))["prompt_id"]
    except urllib.error.HTTPError as e:
        sys.exit("queue error: " + e.read().decode()[:3000])
    except urllib.error.URLError as e:
        sys.exit(f"ComfyUI 연결 실패 ({url}): {e.reason}")
    print(f"queued {pid}")
    t0 = time.time()
    while True:
        hist = json.loads(api(url, f"/history/{pid}"))
        if pid in hist:
            break
        if time.time() - t0 > timeout:
            sys.exit(f"timeout ({timeout}s)")
        time.sleep(2)
    entry = hist[pid]
    if entry["status"]["status_str"] != "success":
        for kind, msg in entry["status"].get("messages", []):
            if kind == "execution_error":
                print(json.dumps(msg, ensure_ascii=False)[:2000])
        sys.exit("generation failed")
    print(f"done {time.time() - t0:.1f}s")
    return entry["outputs"]


def fetch_image(url, img):
    """SaveImage 출력 한 장의 바이트"""
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
    return api(url, f"/view?{q}")


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 게임 아이콘 생성")
    ap.add_argument("--name", required=True, help="파일명 (확장자 없이, 영문 소문자·숫자·_·-)")
    ap.add_argument("--prompt", required=True, help="영문 프롬프트")
    ap.add_argument("--label", default="", help="기록용 한글 이름 (예: 동물 사체). 없으면 기존 기록의 이름 유지")
    ap.add_argument("--seed", type=int, default=None, help="고정 시드 (없으면 랜덤)")
    ap.add_argument("--size", type=int, default=64, help="최종 픽셀 크기 (기본 64)")
    ap.add_argument("--colors", type=int, default=32, help="팔레트 색 수 (기본 32)")
    ap.add_argument("--bg", choices=sorted(BG_COLORS), default="black", help="생성 배경색 (배경 제거 전). 어두운 대상·불·고리 모양은 white")
    ap.add_argument("--no-style", action="store_true", help="그림체 머리말을 붙이지 않음")
    ap.add_argument("--no-suffix", action="store_true", help="배경 제거용 프롬프트 꼬리말을 붙이지 않음")
    ap.add_argument("--force", action="store_true", help="같은 이름 파일이 있으면 덮어씀")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not NAME_RE.fullmatch(a.name):
        sys.exit(f"bad name: {a.name!r} (규칙: <분류>_<id>, 분류 = {'|'.join(CATEGORIES)}, id = 영문 소문자·숫자·- / docs/아이콘_생성.md)")
    dest = ICON_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    text = a.prompt if a.no_suffix else a.prompt.rstrip(" ,.") + PROMPT_SUFFIX.format(bg=BG_COLORS[a.bg])
    if not a.no_style:
        text = STYLE_PREFIX + text
    seed = a.seed if a.seed is not None else random.randint(0, 2**48)
    prompt = build_prompt(text, a.name, seed, a.size, a.colors)

    print(f"seed={seed}")
    outputs = run_workflow(a.url, prompt)
    full = outputs["save_full"]["images"][0]
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetch_image(a.url, outputs["save_icon"]["images"][0]))

    opts = []
    if a.bg != "black":
        opts += ["--bg", a.bg]
    if a.no_style:
        opts.append("--no-style")
    if a.no_suffix:
        opts.append("--no-suffix")
    if a.size != 64:
        opts += ["--size", str(a.size)]
    if a.colors != 32:
        opts += ["--colors", str(a.colors)]
    record(a.name, a.label, a.prompt, seed, opts)

    print(f"icon  {dest}")
    print(f"full  ComfyUI output/{full['subfolder']}/{full['filename']}")


if __name__ == "__main__":
    main()
