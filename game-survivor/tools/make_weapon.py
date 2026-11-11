"""서바이버 무기 그림 — KREA2 Turbo (game-card-world2/tools/icon_common 워크플로우를 빌려 씀).

옆에서 본 모습, **총구가 오른쪽**을 보게 그린다 → 게임에서 조준 각도만큼 돌린다.
결과: game-survivor/images/weapon_<id>.png (투명 배경, 그림 둘레 빈칸을 잘라냄)
기록: game-survivor/docs/그림_목록.md

사용:
  python tools/make_weapon.py --id pistol --seed 1301 --prompt "a modern black semi-automatic handgun"
"""
import argparse
import random
import sys
import time
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent / "game-card-world2" / "tools"))
import icon_common as C  # noqa: E402
from PIL import Image  # noqa: E402

# 현대물 사물 머리말 — 사람 · 손이 끼지 않게 (icon_common 의 판타지 머리말 대신)
PREFIX = ("Stylized modern action game weapon icon, chunky readable shapes, " + C.PAINT
          + "An inanimate object only, no person, no human, no hands, no face, no creature: ")
POSE = ", seen exactly from the side in flat profile, horizontal, the muzzle points to the right edge, the grip points down"

ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True)
ap.add_argument("--prompt", required=True)
ap.add_argument("--seed", type=int, default=None)
ap.add_argument("--size", type=int, default=128)
ap.add_argument("--colors", type=int, default=48)
ap.add_argument("--bg", choices=sorted(C.BG_COLORS), default="white")
ap.add_argument("--url", default="http://127.0.0.1:8188")
a = ap.parse_args()

seed = a.seed if a.seed is not None else random.randint(0, 2**31)
text = PREFIX + a.prompt.rstrip(" ,.") + POSE + C.OBJECT_SUFFIX.format(bg=C.BG_COLORS[a.bg])
print(text, "\nseed", seed)
out = C.run_workflow(a.url, C.build_prompt(text, f"survivor_weapon_{a.id}", seed, a.size, a.colors))
img = Image.open(BytesIO(C.fetch_image(a.url, out["save_icon"]["images"][0]))).convert("RGBA")
img = img.crop(img.split()[3].getbbox())                      # 둘레 빈칸 잘라냄 → 회전 축을 손잡이 쪽에 잡기 쉽게
dest = GAME / "images" / f"weapon_{a.id}.png"
img.save(dest)
print("saved", dest, img.size)

log = GAME / "docs" / "그림_목록.md"
t = log.read_text(encoding="utf-8") if log.exists() else "# 그림 목록\n\n> 생성 스크립트가 남기는 기록. 같은 파일은 덮어쓴다.\n"
entry = f"\n## weapon_{a.id}\n- 생성: {time.strftime('%Y-%m-%d')} · seed `{seed}` · `tools/make_weapon.py --bg {a.bg} --size {a.size}`\n```\n{a.prompt}\n```\n"
import re  # noqa: E402
t = re.sub(rf"\n## weapon_{a.id}\n.*?```\n.*?```\n", "", t, flags=re.S) + entry
log.write_text(t, encoding="utf-8", newline="\n")
