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
    seed = a.seed if a.seed is not None else random.randint(0, 2**31)
    print(f"seed={seed}")
    out = run_workflow(a.url, graph(text, seed, a.gen_w, a.gen_h, a.name))
    im = Image.open(BytesIO(fetch_image(a.url, out["save"]["images"][0]))).convert("RGB")
    im = im.resize((a.out_w, a.out_h), Image.LANCZOS)               # 원본 색 그대로 — 색 줄이기 없음
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    im.save(dest, optimize=True)
    opts = ["(scene-krea2)", f"--out-w {a.out_w}", f"--out-h {a.out_h}"] + (["--tower"] if a.tower else []) + (["--people"] if a.people else []) + (["--knight"] if a.knight else []) + (["--unarmed"] if a.unarmed else []) + (["--serina"] if a.serina else []) + ([f"--cast {a.cast}"] if a.cast else []) + ([f"--dongtap {a.dongtap}"] if a.dongtap else []) + (["--glow"] if a.glow else [])
    record(a.name, a.label, a.prompt, seed, opts, file=f"images/scene/{a.name}.png")
    print(f"scene {dest}  {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
