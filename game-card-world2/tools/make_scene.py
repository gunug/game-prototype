"""시나리오 카드 그림 생성 — 콜렉터북 📜 흔적의 **시나리오 카드** (큰 그림 한 장 + 짧은 이야기).

2026-10-15 확정: **KREA 2 Turbo** · 집 결(deform — make_character_sheet.py 와 같은 문구) · **원본 색 그대로** (색 줄이기 없음).
배경을 지우지 않는다 (장면 그대로). 768×1024 생성 → 360×480 (3:4) → images/scene/<name>.png

사용법:
  python tools/make_scene.py --name scene_tower --label 황금탑 --tower --seed 4242 \
      --prompt "Worm's-eye view from the dusty foot of the tower ..."
  --tower : 탑이 보이는 장면이면 붙인다 — 탑 모양 문구(TOWER)를 덧붙여 장마다 같은 꼴로 나오게
  --people: 사람이 나오는 장면이면 붙인다 — 데포르메 비율 문구
  --knight: 기사 가렛이 나오는 장면 — 게임 그림과 같은 차림 문구
  --serina: 세리나가 나오는 장면 — 게임 그림과 같은 차림 문구
  --dongtap N: 보른의 동탑이 보이는 장면 — N 층까지 올라간 모양. --glow 를 더하면 완성 날 황금으로 빛난다
  구도가 맘에 안 들면 --seed 만 바꾼다. 같은 seed · 같은 글이면 같은 그림
기록: ../docs/아이콘_목록.md
"""
import argparse
import random
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from icon_common import fetch_image, record, run_workflow
from roster_characters import PEOPLE as _PEOPLE
CAST = {cid: desc for cid, label, desc in _PEOPLE}   # 2026-10-19: 사람마다 생김새 — 흔적 그림에서도 같은 얼굴로

SCENE_DIR = Path(__file__).resolve().parent.parent / "images" / "scene"
# 황금탑 모양 — 탑이 보이는 장면마다 그대로 붙인다
TOWER = ("the golden tower: polished gold and pale cream stone, seven stacked round tiers each narrower than the one below, "
         "every tier ringed by a balcony of slender white columns with a band of gold arches and small golden domes, "
         "topped by a tall slender golden needle spire")
# 집 결 — make_character_sheet.py 의 STYLE_DEFORM · PROP_DEFORM(person full) · NOT_REAL 과 같은 말
STYLE = ("stylized fantasy video-game art, hand-painted illustration with visible painterly brushwork, "
         "soft cel-shaded volumes with clean readable shapes, warm vivid colors, gentle rim lighting, "
         "appealing character-design rendering, sharp focus")
PEOPLE = ("all people drawn with stylized deformed proportions: a large expressive head about one fifth of the body height, "
          "compact sturdy body, small hands and feet")
# 기사 가렛 — 게임 그림(portrait_knight)과 같은 차림. 기사가 나오는 장면이면 --knight
KNIGHT = ("the knight: a young man with messy dark brown hair and a determined face, steel shoulder pauldrons and arm plates "
          "over a brown leather vest, a blue tunic underneath, brown leather boots, a plain short sword")
# 무기를 아직 못 가진 때의 기사 (들머리 ~ 두르간) — --knight --unarmed
KNIGHT_UNARMED = ("the knight: a young man with messy dark brown hair and a determined face, steel shoulder pauldrons and arm plates "
                  "over a brown leather vest, a blue tunic underneath, brown leather boots, empty-handed, "
                  "carrying no sword and no weapon at all; a plain belt with NOTHING hanging from it — "
                  "no scabbard, no sheath, no sword hilt, no dagger, no straps at the hip")
# 세리나 — 게임 그림(portrait_archer)과 같은 차림. 세리나가 나오는 장면이면 --serina
SERINA = ("the girl Serina: a cheerful young archer girl with dark brown hair under a green hood and cloak, "
          "a brown leather jerkin, green trousers, brown boots, a quiver on her back")
# 동탑 — 보른이 여관 뒤에 쌓는 탑 (v9.117.0). --dongtap N (지금 몇 층까지 올랐나) · --glow (완성 날 황금으로 빛난다)
DONGTAP = ("the bronze tower behind the roadside wooden inn: a sturdy squat round tower of rough grey fieldstone and "
           "fired brick, each tier ringed by a dull bronze-colored band, plain and humble, wooden scaffolding and ladders")
GLOW = ("THE TOWER IS GLOWING GOLD: on its completion day the whole stone tower blazes with brilliant shining golden light, "
        "every stone and brick turned gleaming gold, radiant golden rays pouring out of every joint, a dazzling golden tower "
        "lighting the scene with warm gold light")   # 빛 문구는 맨 앞에 붙인다 (뒤에 두면 잘 안 먹는다)
# 완성 날 — 회색 돌 문구(DONGTAP)를 빼고 이것만 (돌 문구와 섞으면 금빛이 안 먹는다)
DONGTAP_GOLD = ("the seven-tier tower behind the roadside inn has turned into a dazzling tower of gleaming polished gold, "
                "every block shining gold, golden light radiating from it and bathing the people in warm gold light")
NOT = "no photorealism, not a photo, no gritty realism, no text, no letters, no watermark, no border, no frame"


def graph(text, seed, w, h, name):
    return {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": text}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": ""}},   # cfg 1 이라 빈 칸
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "ks": {"class_type": "KSampler", "inputs": {"model": ["unet", 0], "positive": ["pos", 0], "negative": ["neg", 0],
               "latent_image": ["latent", 0], "seed": seed, "steps": 8, "cfg": 1, "sampler_name": "er_sde",
               "scheduler": "simple", "denoise": 1}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": f"scene/{name}"}},
    }


# 2026-11-06: **A포즈 캐릭터 시트를 기준 그림으로** — KREA2 identity edit (LoRA krea2_identity_edit_v1_2 + comfyui-krea2edit 노드).
#   --ref knight,ally : images/ref/apose_<id>.png 를 첫째 · 둘째 기준으로 넣는다 (둘까지). 얼굴 · 옷 · 머리 크기가 시트를 따른다
REF_DIR = Path(__file__).resolve().parent.parent / "images" / "ref"
REF_NAME = {"knight": "Garret", "ally": "Serina"}   # 글 속에서 부를 이름 (그 밖은 id)


def upload(url, path):
    import requests
    with open(path, "rb") as f:
        r = requests.post(f"{url}/upload/image", files={"image": (path.name, f, "image/png")}, data={"overwrite": "true"})
    r.raise_for_status()
    return r.json()["name"]


def graph_ref(text, seed, w, h, name, refs, boost=4.0, steps=10):
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "krea2_turbo_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "lora": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet", 0], "lora_name": "Krea2\\krea2_identity_edit_v1_2.safetensors", "strength_model": 1.0}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "krea2", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "latent": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "ref_a": {"class_type": "LoadImage", "inputs": {"image": refs[0]}},
        "enc_a": {"class_type": "VAEEncode", "inputs": {"pixels": ["ref_a", 0], "vae": ["vae", 0]}},
        "patch": {"class_type": "Krea2EditModelPatch", "inputs": {"model": ["lora", 0], "source_latent": ["enc_a", 0], "ref_boost": boost,
                  "ref_boost_a": boost if len(refs) > 1 else 1.0, "fit_mode": "fit", "vae": ["vae", 0], "source_image": ["ref_a", 0],
                  "target_latent": ["latent", 0]}},
        "pos": {"class_type": "Krea2EditGroundedEncode", "inputs": {"clip": ["clip", 0], "prompt": text, "image": ["ref_a", 0], "grounding_px": 768, "system_prompt": ""}},
        "neg": {"class_type": "Krea2EditGroundedEncode", "inputs": {"clip": ["clip", 0], "prompt": "", "image": ["ref_a", 0], "grounding_px": 768, "system_prompt": ""}},
        "ks": {"class_type": "KSampler", "inputs": {"model": ["patch", 0], "positive": ["pos", 0], "negative": ["neg", 0],
               "latent_image": ["latent", 0], "seed": seed, "steps": steps, "cfg": 1, "sampler_name": "euler",
               "scheduler": "simple", "denoise": 1}},
        "dec": {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": f"scene/{name}"}},
    }
    if len(refs) > 1:                                   # 둘째 사람 — RoPE frame 2 (README: 두 사람은 한 번에 넣는다)
        g["ref_b"] = {"class_type": "LoadImage", "inputs": {"image": refs[1]}}
        g["enc_b"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["ref_b", 0], "vae": ["vae", 0]}}
        g["patch"]["inputs"].update(source_latent_b=["enc_b", 0], source_image_b=["ref_b", 0])
        for k in ("pos", "neg"):
            g[k]["inputs"]["image_b"] = ["ref_b", 0]
    return g


def main():
    ap = argparse.ArgumentParser(description="ComfyUI 시나리오 카드 그림 (KREA2)")
    ap.add_argument("--name", required=True, help="파일명 scene_<id>")
    ap.add_argument("--prompt", required=True, help="영문 — 장면 · 앵글")
    ap.add_argument("--label", default="")
    ap.add_argument("--tower", action="store_true", help="탑이 보이는 장면 — 탑 모양 문구를 붙인다")
    ap.add_argument("--people", action="store_true", help="사람이 나오는 장면 — 데포르메 비율 문구를 붙인다")
    ap.add_argument("--knight", action="store_true", help="기사가 나오는 장면 — 기사 차림 문구를 붙인다 (--people 도 함께 켠다)")
    ap.add_argument("--unarmed", action="store_true", help="--knight 와 함께 — 칼 없는 기사 (무기를 갖기 전 장면)")
    ap.add_argument("--cast", default="", help="나오는 사람 id (쉼표) — roster_characters.py 의 생김새 묘사를 붙인다. 예: cook,shieldsmith")
    ap.add_argument("--serina", action="store_true", help="세리나가 나오는 장면 — 세리나 차림 문구 (--people 도 함께 켠다)")
    ap.add_argument("--dongtap", type=int, default=0, help="동탑이 보이는 장면 — 지금 몇 층까지 올랐나 (1~7)")
    ap.add_argument("--glow", action="store_true", help="--dongtap 과 함께 — 완성 날 황금으로 빛나는 동탑")
    ap.add_argument("--ref", default="", help="기준 캐릭터 시트 id (쉼표, 둘까지) — images/ref/apose_<id>.png. 예: knight,ally")
    ap.add_argument("--ref-boost", type=float, default=1.0, help="기준 그림을 얼마나 따르나 — 1 (기본: 생김새는 지키고 표정 · 자세는 장면대로) · 4 면 표정 · 자세까지 시트에 굳는다")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--gen-w", type=int, default=768)
    ap.add_argument("--gen-h", type=int, default=1024)
    ap.add_argument("--out-w", type=int, default=360)
    ap.add_argument("--out-h", type=int, default=480)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    if not a.name.startswith("scene_"):
        sys.exit(f"bad name: {a.name!r} (규칙: scene_<id>)")
    dest = SCENE_DIR / f"{a.name}.png"
    if dest.exists() and not a.force:
        sys.exit(f"exists: {dest} (--force 로 덮어쓰기)")

    if a.knight or a.serina or a.cast:
        a.people = True
    text = ((f"{GLOW}. " if a.glow else "") + a.prompt.rstrip(" .") + "."
            + (f" {KNIGHT_UNARMED if a.unarmed else KNIGHT}." if a.knight else "")
            + (f" {SERINA}." if a.serina else "")
            + "".join(f" {CAST[c]}." for c in a.cast.split(",") if c in CAST)
            + (" " + PEOPLE + "." if a.people else "")
            + (f" The tower: {TOWER}." if a.tower else "")
            + (f" {DONGTAP_GOLD}." if a.glow else f" {DONGTAP}, {a.dongtap} tier{'s' if a.dongtap > 1 else ''} tall so far." if a.dongtap else "")
            + f" {STYLE}. {NOT}.")
    refs = [x for x in a.ref.split(",") if x]
    if len(refs) > 2:
        sys.exit("--ref 는 둘까지")
    if refs:
        # 기준 그림이 생김새를 맡는다 — 차림 문구(--knight · --serina · --cast)는 붙이지 않고, 장면 글은 '이 사람을 이 장면에' 꼴로
        who = " and ".join(f"{REF_NAME.get(x, x)} (the {'first' if i == 0 else 'second'} reference character)" for i, x in enumerate(refs))
        text = ((f"{GLOW}. " if a.glow else "")
                + f"Draw {who} in a new scene. Keep {'their' if len(refs) > 1 else 'the'} identity from the reference sheet — face shape, "
                + "hair, outfit, colors and stylized proportions — but give them NEW lively facial expressions and natural poses "
                + "that fit this moment, not the neutral sheet expression or the stiff A-pose. "   # v2: 'exact face' 는 표정까지 시트에 묶었다
                + a.prompt.rstrip(" .") + "."
                + (f" The tower: {TOWER}." if a.tower else "")
                + (f" {DONGTAP_GOLD}." if a.glow else f" {DONGTAP}, {a.dongtap} tier{'s' if a.dongtap > 1 else ''} tall so far." if a.dongtap else "")
                + f" {STYLE}.")
    seed = a.seed if a.seed is not None else random.randint(0, 2**31)
    print(f"seed={seed}")
    if refs:
        names = [upload(a.url, REF_DIR / f"apose_{x}.png") for x in refs]
        out = run_workflow(a.url, graph_ref(text, seed, a.gen_w, a.gen_h, a.name, names, a.ref_boost))
    else:
        out = run_workflow(a.url, graph(text, seed, a.gen_w, a.gen_h, a.name))
    im = Image.open(BytesIO(fetch_image(a.url, out["save"]["images"][0]))).convert("RGB")
    im = im.resize((a.out_w, a.out_h), Image.LANCZOS)               # 원본 색 그대로 — 색 줄이기 없음
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)
    opts = ["(scene-krea2)", f"--out-w {a.out_w}", f"--out-h {a.out_h}"] + (["--tower"] if a.tower else []) + (["--people"] if a.people else []) + (["--knight"] if a.knight else []) + (["--unarmed"] if a.unarmed else []) + (["--serina"] if a.serina else []) + ([f"--cast {a.cast}"] if a.cast else []) + ([f"--dongtap {a.dongtap}"] if a.dongtap else []) + (["--glow"] if a.glow else []) + ([f"--ref {a.ref}", f"--ref-boost {a.ref_boost}"] if refs else [])
    record(a.name, a.label, a.prompt, seed, opts, file=f"images/scene/{a.name}.png")
    print(f"scene {dest}  {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
