"""캐릭터 시트 생성 — KREA2 체인 + BiRefNet-HR 배경제거 (2026-10-06)

ComfyUI 워크플로우 `KREA2 체인 + BiRefNet-HR 배경제거.json` 을 그대로 API 형식으로 옮긴 것.
**사람과 크리처는 이제 전부 이 스크립트로 뽑는다** (make_icon_character.py 는 쓰지 않는다).

한 번 돌리면 세 장이 나오고, 셋 다 게임의 제 자리로 들어간다.
  얼굴   → images/icon/card_<id>.png        64x64 · 32색   (카드)
  상반신 → images/portrait/bust_<id>.png    192x256        (인스펙터)
  전신   → images/portrait/portrait_<id>.png 192x256       (전투 · 줄 토큰)

체인 (모델은 KREA 2 Turbo 하나만 올린다 — 3단 전부 같은 UNet/CLIP/VAE 를 쓴다):
  1단  전신 720x1280 을 글에서 생성 (8스텝 · cfg 1 · er_sde)
  2단  전신에서 **얼굴을 찾아** 그 자리를 기준으로 넓게 잘라 720x1024 → 다시 샘플링 (denoise 0.12)
  3단  상반신에서 다시 얼굴을 찾아 바짝 잘라 1024x1024 → 다시 샘플링 (denoise 0.05)
  세 장 모두 색보정(밝기·대비·채도) 뒤 BiRefNet General-HR 로 배경을 지워 투명 PNG 로 받는다.
  크롭은 좌표가 아니라 **얼굴 검출 결과**를 기준으로 잡으므로 자세가 바뀌어도 그대로 쓴다.

쓰기:
  python tools/make_character_sheet.py --name archer --label 궁수 --kind person \
      --desc "a young human archer, short brown hair, green hood, wooden bow"
  python tools/make_character_sheet.py --name wolf --label 늑대 --kind creature \
      --desc "a grey timber wolf, thick fur, yellow eyes"

크리처는 `--kind creature` 를 꼭 준다 — 사람·인간형이 끼지 않게 프롬프트에 못을 박고,
전신은 **왼쪽을 보게** 그린다 (원정이 왼→오른쪽이라 기다리는 쪽이 왼쪽을 본다).
"""
import argparse
import random
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

import icon_common as C

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "images" / "icon"
PORTRAIT_DIR = ROOT / "images" / "portrait"

# ── 그림체 — 워크플로우 기본 톤 그대로 (2026-10-06 사용자 확정) ──────────────
STYLE = (
    "AAA western video-game key art, semi-realistic digital oil painting with visible painterly "
    "brushwork and textured impasto, cinematic rim lighting, muted desaturated palette with warm "
    "highlights, concept-art rendering, sharp focus"
)
NOT_ANIME = (
    "NOT anime, NOT manga, NOT cel-shaded, no flat colors, no black outlines, no lineart, "
    "no chibi, no big glossy eyes, no text, no watermark"
)
# ── 데포르메 결 (2026-10-06) — 실사 말고 **얼굴이 큼직한** 게임 그림 ──────────
#   사람은 머리를 키워 다섯 머리 키쯤으로, 이목구비를 크고 또렷하게. 크리처도 같은 결로 간다
STYLE_DEFORM = (
    "stylized fantasy video-game character art, hand-painted illustration with visible painterly "
    "brushwork, soft cel-shaded volumes with clean readable shapes, warm vivid colors, "
    "gentle rim lighting, appealing character-design rendering, sharp focus"
)
NOT_REAL = (
    "no photorealism, not a photo, no hyperreal skin pores, no hyperreal fur, no wildlife photography, "
    "no gritty realism, no text, no watermark, no extra characters"
)
PROP_DEFORM = {                                                  # 단계마다 '얼굴을 키운다'고 못을 박는다
    "person": {
        "full": ("stylized deformed proportions: a large expressive head about one fifth of the "
                 "body height, compact sturdy body, small hands and feet"),
        "upper": "a large expressive head, broad clear facial features, simplified stylized anatomy",
        "face": ("a big round-cheeked face filling the frame, large clear eyes, bold simple features, "
                 "soft smooth skin shading"),
    },
    "bug": {        # 거미 · 게 · 벌레 — 머리가 아니라 **몸통**을 키운다
        "full": ("stylized deformed proportions: a big round body about half the whole height, "
                 "short chunky legs, simple bold shapes"),
        "upper": "a big round body, large glossy eyes, simple bold shapes",
        "face": "a big round front body filling the frame, large glossy eyes, simple bold shapes, smooth shading",
    },
    "creature": {   # 2026-10-08: **사람 것과 같은 문구**를 쓴다 (다리 · 발만 짐승 말로)
        "full": ("stylized deformed proportions: a large expressive head about one fifth of the "
                 "body height, compact sturdy body, short sturdy legs and small paws"),
        "upper": "a large expressive head, broad clear features, simplified stylized anatomy",
        "face": ("a big round-cheeked face filling the frame, large clear eyes, bold simple features, "
                 "soft smooth shading"),
    },
}
# 배경 — 잘라내기 좋게 민짜가 기본. --bg scene 이면 워크플로우 예시처럼 배경을 그린다
BG_PLAIN = "plain flat neutral grey studio backdrop, no scenery, no props, no other characters"

# 사람 — 카드 얼굴은 정면 (크리처와 달리 좌우를 뒤집어 쓰지 않는다)
PERSON = {
    "full": ("Full-body character splash art of {desc}, standing in a relaxed ready stance, "
             "facing the viewer, body turned three-quarters, whole body visible from head to toe, "
             "realistic human proportions and anatomy, centered composition"),
    "upper": ("Upper-body character portrait of {desc}, facing the viewer, shoulders squared, "
              "torso turned three-quarters, realistic anatomy and skin texture"),
    "face": ("Close-up face portrait of {desc}, facing the viewer, realistic facial anatomy, "
             "detailed skin texture"),
}
# 크리처 — 사람·인간형이 끼지 않게 단계마다 못을 박는다. 전신은 **왼쪽**을 본다
# 2026-10-08: **사람 금지만 남긴다.** 전엔 여기 'true natural animal anatomy and proportions' 가 붙어 있어
#   뒤에 붙이는 데포르메 문구와 싸웠다 (앞 문구가 이겨 크리처만 반실사로 나왔다).
#   '제 비율' 문구는 real 결에서만 붙인다
# 2026-10-08 ②: **살짝 의인화**를 허락한다 — 눈 · 눈썹에 감정이 읽히되 얼굴은 짐승 얼굴 그대로.
#   사람 얼굴 · 사람 살갗 · 옷 · 손 · 두 발 서기는 그대로 막는다
NO_HUMAN = ("an animal only: no human face, no human skin, no person, no humanoid body, "
            "not standing on two legs, no hands, no clothing, no armor, no weapon, no rider")
ANTHRO = (", gently anthropomorphic FACE ONLY: readable emotion in the eyes and brow, an expressive "
          "cartoon-character face, while the head stays an animal head with a real muzzle and animal ears")
# 전신은 **제 자세**를 지킨다 — 의인화 문구가 두 발로 세워 버리는 것을 막는다 (거미 · 악어가 섰다)
STANCE = (", standing in the natural stance of its species on all of its legs, body horizontal, "
          "not upright, not bipedal, not standing on two legs, not rearing up")
REAL_ANIM = ", true natural animal anatomy and proportions for the species"
# 2026-10-08: **크리처 틀 = 사람(기사) 틀 그대로.** 결이 안 맞던 까닭은 틀이 따로 자랐기 때문이다.
#   사람 문구를 그대로 쓰고, 크리처라는 표시만 한 마디씩 더한다 (짐승 머리 · 네 발 · 옷 없음).
#   `--style real` 일 때만 '제 비율' 문구가 붙는다 ({anat} · {skin})
BEAST = (", an animal character: an animal head with a real muzzle and animal ears, "
         "no human face, no human skin, no clothing, no hands")
BEAST_BUG = ", a creature character: no human face, no human skin, no clothing, no hands"
# 전신에만 — 자세를 못 박지 않으면 몸을 세워 앉는다 (악어가 그랬다)
STANCE = (", all of its feet on the ground, body held horizontal in the natural stance of its species, "
          "not upright, not sitting up, not rearing up, not bipedal")
# 거미 · 게 · 벌레처럼 **얼굴이랄 것이 없는 몸** — '둥근 뺨 · 큰 눈'이 걸릴 데가 없어 따로 적는다
BUG = (", one big round body, simplified chunky legs, a cluster of large glossy eyes, "
       "smooth shell with simple bold markings, no fine hair detail")
CREATURE = {
    "full": ("Full-body character splash art of {desc}, standing in a relaxed ready stance, "
             "side view facing to the left, body turned three-quarters, whole body visible from head to toe, "
             "centered composition" + "{beast}" + STANCE + "{body}{anat}"),
    "upper": ("Upper-body character portrait of {desc}, facing the viewer, head and chest, "
              "body turned three-quarters" + "{beast}{body}{anat}{skin}"),
    "face": ("Close-up face portrait of {desc}, facing the viewer" + "{beast}{body}{anat}{skin}"),
}
KINDS = {"person": PERSON, "creature": CREATURE}

NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# 나오는 파일 — (단계, 저장 경로, 크기, 팔레트 색 수, 세로 정렬)
OUTS = {
    "face":  ("card_{n}.png",     ICON_DIR,     (64, 64),    32,   "center"),
    "upper": ("bust_{n}.png",     PORTRAIT_DIR, (192, 256),  None, "bottom"),
    "full":  ("portrait_{n}.png", PORTRAIT_DIR, (192, 256),  None, "bottom"),
}


def prompt_of(kind, stage, desc, bg, style="real", prop=True, body="beast"):
    """단계별 프롬프트 = 틀 + 설명 + 그림체 + 배경 + 금지"""
    deform = style == "deform"
    head = KINDS[kind][stage].format(
        desc=desc.rstrip(" ,."),
        beast=BEAST_BUG if body == "bug" else BEAST,              # 벌레에겐 주둥이 · 귀를 말하지 않는다
        body=BUG if body == "bug" else "",                        # 거미 · 게 · 벌레는 몸꼴을 따로 적는다
        anat="" if (deform and prop) else REAL_ANIM,              # 데포르메면 '제 비율' 문구를 빼 둔다
        skin="" if deform else ", detailed fur and skin texture")
    if deform:                                                   # 실사 문구를 데포르메 문구로 갈아 끼운다
        head = (head.replace("realistic human proportions and anatomy", PROP_DEFORM["person"]["full"])
                    .replace("realistic anatomy and skin texture", PROP_DEFORM["person"]["upper"])
                    .replace("realistic facial anatomy, detailed skin texture", PROP_DEFORM["person"]["face"])
                    .replace("detailed fur and skin texture", PROP_DEFORM["creature"]["face"]))
        if kind == "creature" and prop:                           # 머리 · 몸통이 없는 것(수렁 팔 …)은 이 문구를 빼야 짐승이 안 된다
            head += ", " + PROP_DEFORM["bug" if body == "bug" else "creature"][stage]
        tail = STYLE_DEFORM + ", " + (bg if bg else BG_PLAIN)
        return f"{head}. {tail}. {NOT_REAL}."
    tail = STYLE + ", " + (bg if bg else BG_PLAIN)
    return f"{head}. {tail}. {NOT_ANIME}."


def build(a, texts):
    """워크플로우를 API 형식으로. 노드 이름은 원본 워크플로우의 역할 그대로"""
    sub = f"krea2_chain/{a.name}"
    g = {
        # ── 모델 한 벌 (3단 공용) ──
        "unet": {"class_type": "UNETLoader",
                 "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader",
                 "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": ""}},   # cfg 1 이라 빈 칸
        "birefnet": {"class_type": "AutoDownloadBiRefNetModel",
                     "inputs": {"model_name": "General-HR", "device": "AUTO", "dtype": "float32"}},
        "clipseg": {"class_type": "DownloadAndLoadCLIPSeg",
                    "inputs": {"model": "Kijai/clipseg-rd64-refined-fp16"}},
        # ── 1단 전신 ──
        "pos_full": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": texts["full"]}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": a.width, "height": a.height, "batch_size": 1}},
        "ks_full": {"class_type": "KSampler", "inputs": {
            "model": ["unet", 0], "positive": ["pos_full", 0], "negative": ["neg", 0], "latent_image": ["latent", 0],
            "seed": a.seed, "steps": a.steps, "cfg": 1, "sampler_name": "er_sde", "scheduler": "simple", "denoise": 1}},
        "dec_full": {"class_type": "VAEDecode", "inputs": {"samples": ["ks_full", 0], "vae": ["vae", 0]}},
        # ── 2단 상반신 — 전신에서 얼굴을 찾아 그 자리 기준으로 넓게 자른다 ──
        "seg_full": {"class_type": "BatchCLIPSeg", "inputs": {
            "images": ["dec_full", 0], "text": a.seg_text, "threshold": 0.5, "binary_mask": True,
            "combine_mask": False, "use_cuda": True, "blur_sigma": 0, "image_bg_level": 0.5,
            "invert": False, "opt_model": ["clipseg", 0]}},
        "mask_upper": {"class_type": "MaskComposite", "inputs": {                 # 찾은 자리를 아래로 늘려 몸을 담는다
            "destination": ["seg_full", 0], "source": ["seg_full", 0], "x": 0, "y": a.upper_down, "operation": "add"}},
        "crop_upper": {"class_type": "ImageCropByMaskAndResize", "inputs": {
            "image": ["dec_full", 0], "mask": ["mask_upper", 0], "base_resolution": 768,
            "padding": a.upper_pad, "min_crop_resolution": 128, "max_crop_resolution": 2048}},
        "rs_upper": {"class_type": "ImageResizeKJv2", "inputs": {
            "image": ["crop_upper", 0], "width": 720, "height": 1024, "upscale_method": "lanczos",
            "keep_proportion": "crop", "pad_color": "0, 0, 0", "crop_position": "center",
            "divisible_by": 16, "device": "cpu"}},
        "pos_upper": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": texts["upper"]}},
        "enc_upper": {"class_type": "VAEEncode", "inputs": {"pixels": ["rs_upper", 0], "vae": ["vae", 0]}},
        "ks_upper": {"class_type": "KSampler", "inputs": {
            "model": ["unet", 0], "positive": ["pos_upper", 0], "negative": ["neg", 0], "latent_image": ["enc_upper", 0],
            "seed": 0, "steps": a.steps, "cfg": 1, "sampler_name": "er_sde", "scheduler": "simple",
            "denoise": a.denoise_upper}},
        "dec_upper": {"class_type": "VAEDecode", "inputs": {"samples": ["ks_upper", 0], "vae": ["vae", 0]}},
        # ── 3단 얼굴 — 상반신에서 다시 얼굴을 찾아 바짝 자른다 ──
        "seg_upper": {"class_type": "BatchCLIPSeg", "inputs": {
            "images": ["dec_upper", 0], "text": a.seg_text, "threshold": 0.5, "binary_mask": True,
            "combine_mask": False, "use_cuda": True, "blur_sigma": 0, "image_bg_level": 0.5,
            "invert": False, "opt_model": ["clipseg", 0]}},
        "mask_face": {"class_type": "MaskComposite", "inputs": {
            "destination": ["seg_upper", 0], "source": ["seg_upper", 0], "x": 0, "y": a.face_down, "operation": "add"}},
        "crop_face": {"class_type": "ImageCropByMaskAndResize", "inputs": {
            "image": ["dec_upper", 0], "mask": ["mask_face", 0], "base_resolution": 1024,
            "padding": a.face_pad, "min_crop_resolution": 128, "max_crop_resolution": 2048}},
        "rs_face": {"class_type": "ImageResizeKJv2", "inputs": {
            "image": ["crop_face", 0], "width": 1024, "height": 1024, "upscale_method": "lanczos",
            "keep_proportion": "crop", "pad_color": "0, 0, 0", "crop_position": "center",
            "divisible_by": 16, "device": "cpu"}},
        "pos_face": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": texts["face"]}},
        "enc_face": {"class_type": "VAEEncode", "inputs": {"pixels": ["rs_face", 0], "vae": ["vae", 0]}},
        "ks_face": {"class_type": "KSampler", "inputs": {
            "model": ["unet", 0], "positive": ["pos_face", 0], "negative": ["neg", 0], "latent_image": ["enc_face", 0],
            "seed": 0, "steps": a.steps, "cfg": 1, "sampler_name": "er_sde", "scheduler": "simple",
            "denoise": a.denoise_face}},
        "dec_face": {"class_type": "VAEDecode", "inputs": {"samples": ["ks_face", 0], "vae": ["vae", 0]}},
    }
    # ── 색보정은 **저장 쪽 가지에만** 건다 (다음 단계의 크롭 입력은 원본 그대로) ──
    for stage, dec in (("full", "dec_full"), ("upper", "dec_upper"), ("face", "dec_face")):
        g[f"cc_{stage}"] = {"class_type": "LayerColor: BrightnessContrastV2", "inputs": {
            "image": [dec, 0], "brightness": a.brightness, "contrast": a.contrast, "saturation": a.saturation}}
        g[f"rgba_{stage}"] = {"class_type": "RembgByBiRefNet",
                              "inputs": {"model": ["birefnet", 0], "images": [f"cc_{stage}", 0]}}
        g[f"save_{stage}"] = {"class_type": "SaveImage", "inputs": {
            "images": [f"cc_{stage}", 0], "filename_prefix": f"{sub}_{stage}"}}
        g[f"save_rgba_{stage}"] = {"class_type": "SaveImage", "inputs": {
            "images": [f"rgba_{stage}", 0], "filename_prefix": f"{sub}_{stage}_rgba"}}
    return g


def fit(im, size, colors, valign):
    """투명 여백을 잘라내고 제 크기로 줄여 투명 바탕에 올림 (세로 정렬 선택)"""
    im = im.convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        im = im.crop(box)
    w, h = size
    s = min(w / im.width, h / im.height)
    nw, nh = max(1, round(im.width * s)), max(1, round(im.height * s))
    im = im.resize((nw, nh), Image.LANCZOS if s > 0.5 else Image.BOX)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(im, ((w - nw) // 2, h - nh if valign == "bottom" else (h - nh) // 2))
    if colors:                                                   # 카드 아이콘만 팔레트를 줄인다 (기존 규격)
        rgb, alpha = out.convert("RGB"), out.getchannel("A")
        rgb = rgb.quantize(colors=colors, dither=Image.Dither.NONE).convert("RGB")
        out = Image.merge("RGBA", (*rgb.split(), alpha))
    return out


def main():
    ap = argparse.ArgumentParser(description="KREA2 체인 + BiRefNet-HR — 캐릭터 얼굴·상반신·전신 한 벌")
    ap.add_argument("--name", required=True, help="id (영문 소문자·숫자·-). 예: archer → card_archer · bust_archer · portrait_archer")
    ap.add_argument("--kind", choices=sorted(KINDS), required=True, help="person: 사람 / creature: 크리처 (사람이 안 끼게 못을 박음)")
    ap.add_argument("--desc", required=True, help="영문 묘사 — 세 단계가 같은 묘사를 쓴다 (머리색·옷·종 따위)")
    ap.add_argument("--label", default="", help="기록용 한글 이름 (예: 궁수)")
    ap.add_argument("--bg", default="", help="배경 묘사. 비우면 잘라내기 좋은 민짜 배경")
    ap.add_argument("--body", choices=("beast", "bug"), default="beast",
                    help="몸꼴 — beast: 머리 달린 짐승 / bug: 거미 · 게 · 벌레(몸통을 키운다)")
    ap.add_argument("--no-prop", action="store_true",
                    help="데포르메 비율 문구를 붙이지 않는다 — 머리 · 몸통이 없는 것(수렁 팔 · 탑의 눈)에 쓴다")
    ap.add_argument("--style", choices=("real", "deform"), default="real",
                    help="그림 결 — real: 워크플로우 기본 톤(반실사) / deform: 데포르메, 얼굴을 키운 게임 그림")
    ap.add_argument("--seed", type=int, default=None, help="1단 시드 (없으면 랜덤). 구도가 맘에 안 들면 이것만 바꾼다")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--denoise-upper", type=float, default=0.12, help="2단 리파인 세기 (크면 또렷하나 얼굴이 달라짐)")
    ap.add_argument("--denoise-face", type=float, default=0.05, help="3단 리파인 세기")
    ap.add_argument("--upper-pad", type=int, default=85, help="상반신 크롭량 — 키우면 더 넓게 담김")
    ap.add_argument("--upper-down", type=int, default=170, help="상반신 세로 연장량 — 키우면 얼굴이 위로 가고 몸이 더 담김")
    ap.add_argument("--face-pad", type=int, default=60, help="얼굴 크롭량 — 줄이면 얼굴에 바짝 붙음")
    ap.add_argument("--face-down", type=int, default=10, help="얼굴 세로 연장량")
    # 2026-10-07: 색보정 기본을 **1 (손대지 않음)** 로 — 대비 1.5 가 그림자를 먹어 얼굴이 뭉개졌다
    ap.add_argument("--brightness", type=float, default=1.0)
    ap.add_argument("--contrast", type=float, default=1.0)
    ap.add_argument("--saturation", type=float, default=1.0)
    ap.add_argument("--seg-text", default="face", help="CLIPSeg 로 찾을 것 (크리처는 head 가 나을 수 있음)")
    ap.add_argument("--only", default="", help="일부만 저장 — face,upper,full 중 쉼표로 (그림은 체인이라 어차피 다 돌린다)")
    ap.add_argument("--card-from", choices=("face", "upper", "full"), default="face",
                    help="카드에 쓸 그림. 얼굴이랄 것이 없어 얼굴 검출이 빗나가는 것(바위 등껍질 · 거미 …)은 full 로 — 통째로 담아야 읽힌다")
    ap.add_argument("--force", action="store_true", help="같은 파일이 있으면 덮어씀")
    ap.add_argument("--out-dir", default="", help="시험용 — 게임 폴더 대신 이 폴더에 저장한다 (기록도 남기지 않음)")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not NAME_RE.fullmatch(a.name):
        sys.exit(f"bad name: {a.name!r} (영문 소문자·숫자·-)")
    want = [s.strip() for s in a.only.split(",") if s.strip()] or list(OUTS)
    bad = [s for s in want if s not in OUTS]
    if bad:
        sys.exit(f"--only 는 {', '.join(OUTS)} 중에서: {bad}")
    out_dir = Path(a.out_dir) if a.out_dir else None              # 시험용 폴더
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    dests = {s: (out_dir or OUTS[s][1]) / OUTS[s][0].format(n=a.name) for s in want}
    exists = [p for p in dests.values() if p.exists()]
    if exists and not a.force:
        sys.exit("exists: " + ", ".join(str(p) for p in exists) + " (--force 로 덮어쓰기)")
    if a.seed is None:
        a.seed = random.randrange(2 ** 31)

    texts = {s: prompt_of(a.kind, s, a.desc, a.bg, a.style, not a.no_prop, a.body) for s in ("full", "upper", "face")}
    for s in ("full", "upper", "face"):
        print(f"\n[{s}] {texts[s]}")
    print(f"\nseed {a.seed} · {a.kind} · {a.width}x{a.height}")
    outs = C.run_workflow(a.url, build(a, texts), timeout=1800)

    opts = [f"--kind {a.kind}", f"--style {a.style}", f"--body {a.body}"] + (["--no-prop"] if a.no_prop else []) + [ f"--card-from {a.card_from}", f"--seg-text {a.seg_text}",
            f"--denoise-upper {a.denoise_upper}", f"--denoise-face {a.denoise_face}",
            f"--upper-pad {a.upper_pad}", f"--upper-down {a.upper_down}",
            f"--face-pad {a.face_pad}", f"--face-down {a.face_down}"]
    for s in want:
        node = f"save_rgba_{a.card_from if s == 'face' else s}"   # 카드만 다른 단계에서 떠올 수 있다
        imgs = outs.get(node, {}).get("images") or []
        if not imgs:
            sys.exit(f"no output: {node}")
        raw = Image.open(BytesIO(C.fetch_image(a.url, imgs[0])))
        fname, folder, size, colors, valign = OUTS[s]
        dest = (out_dir or folder) / fname.format(n=a.name)
        fit(raw, size, colors, valign).save(dest)
        print(f"saved {dest}  ({raw.size[0]}x{raw.size[1]} → {size[0]}x{size[1]})")
        if out_dir:
            continue                                              # 시험판은 기록하지 않는다
        rel = dest.relative_to(ROOT).as_posix()
        C.record(dest.stem, f"{a.label} — {s}" if a.label else "", texts["face" if s == "face" else s],
                 a.seed, opts, file=f"{rel}")
    print("\n원본 큰 그림: ComfyUI/output/krea2_chain/")


if __name__ == "__main__":
    main()
