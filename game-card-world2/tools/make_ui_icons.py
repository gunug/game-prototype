"""화면에 쓰이는 이모지를 대신할 UI 아이콘을 한꺼번에 뽑는다 (v3.5.0).

이모지는 기기마다 그림이 달라 게임 화면이 들쭉날쭉해진다. 여기서 뽑은 64px 아이콘을
index.html 의 ICONS 표(id → 파일명)로만 쓰고, 화면 코드에는 이모지를 직접 쓰지 않는다.

사용: python tools/make_ui_icons.py            (이미 있는 파일은 건너뜀)
      python tools/make_ui_icons.py --only ui_aim ui_tree
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "images" / "icon"

# (파일명, 한글 이름, 영문 프롬프트, 흰 배경 여부)
ICONS = [
    ("ui_aim",      "목적",       "a round archery target board with three rings and one arrow stuck in the center", False),
    ("ui_tree",     "길",         "a small bare branching tree diagram carved from wood, trunk splitting into three branches", False),
    ("ui_book",     "콜렉터북",   "a thick closed leather-bound book with a bone clasp", False),
    ("ui_craft",    "조합",       "a stone-headed hammer with a wooden handle, lying flat", True),
    ("ui_gear",     "정비",       "a bundle of simple repair tools: a leather strap and a bone awl tied together", False),
    ("ui_field",    "필드",       "a short stone dagger planted upright in a patch of ground", True),
    ("ui_settings", "설정",       "a simple stone gear wheel with six teeth", True),
    ("ui_recipe",   "조합법",     "a small clay flask with a cork stopper and a bubbling neck", False),
    ("ui_trace",    "흔적",       "a rolled open parchment scroll with faint scratch marks", False),
    ("ui_tag",      "태그",       "a small leather label tag with a hole and a short cord", False),
    ("ui_boss",     "보스",       "a simple heavy crown made of rough gold with three points", True),
    ("ui_key",      "열쇠",       "an old iron key with a round bow and simple teeth", True),
    ("ui_basket",   "채집",       "a woven straw gathering basket seen from the side", False),
    ("ui_paw",      "전리품",     "a single animal paw print pressed into soft earth", False),
    ("ui_parts",    "부품",       "a bolt and a nut made of dark metal lying together", True),
    ("ui_fire",     "불",         "a small campfire flame above two crossed sticks", True),
    ("ui_shield",   "갑옷",       "a small round wooden shield with a leather rim", False),
    ("ui_star",     "표식",       "a single bright five pointed star", True),
    ("ui_pin",      "찍기",       "a push pin with a round head, seen at an angle", False),
    ("ui_note",     "수첩",       "a small worn notebook with a leather cover and a bone pen clipped on", False),
    ("ui_hand",     "조작",       "a pointing hand glove made of leather, index finger extended upward", False),
    ("ui_xp",       "경험치",     "a four pointed sparkle of light", True),
    ("ui_down",     "빈사",       "a single red drop of blood", True),
    ("ui_warn",     "주의",       "a triangular warning sign made of wood with an exclamation mark", False),
    ("ui_nature",   "자연",       "a single green leaf sprig with two leaves", False),
    ("ui_forge",    "가공",       "a stone chisel and a small hammer crossed", True),
    ("ui_tools",    "도구",       "a hand axe and a bone awl crossed", False),
    ("ui_build",    "건축재료",   "three stacked clay bricks", False),
    ("ui_food",     "음식",       "a roasted meat leg on a bone", False),
    ("ui_trident",  "자루",       "a three pronged bone spear head", False),
    ("ui_bow",      "줄",         "a simple wooden hunting bow with a drawn string", False),
    ("ui_rope",     "끈",         "a coil of twisted plant fiber rope", False),
    ("ui_bag",      "담기",       "a leather backpack with shoulder straps", False),
    ("ui_rock",     "돌가죽 굴",  "a rough grey boulder with cracks", False),
    ("ui_web",      "거미 둥지",  "a round spider web with sparse threads", True),
    ("ui_mushroom", "늪지 무덤",  "a single mushroom with a wide speckled cap", False),
    ("ui_shell",    "껍질 동굴",  "a spiral sea shell", False),
    ("ui_run",      "원정 중",    "a pair of worn leather boots with mud on them", False),
    ("ui_clip",     "기록",       "a flat wooden board with a bone clip holding a sheet", False),
    ("card_prelude", "들머리",    "a narrow dirt path between low grassy mounds, with a few loose stones and a dry branch", False),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    todo = [x for x in ICONS if not args.only or x[0] in args.only]
    made, skipped, failed = [], [], []
    for name, label, prompt, white in todo:
        if (OUT / f"{name}.png").exists() and not args.force:
            skipped.append(name)
            continue
        cmd = [sys.executable, str(HERE / "make_icon_object.py"), "--name", name, "--label", label, "--prompt", prompt]
        if white:
            cmd += ["--bg", "white"]
        print(f"▶ {name} — {label}", flush=True)
        r = subprocess.run(cmd, cwd=str(HERE.parent))
        (made if r.returncode == 0 else failed).append(name)
    print(f"\n만듦 {len(made)} · 건너뜀 {len(skipped)} · 실패 {len(failed)}")
    if failed:
        print("실패:", " ".join(failed))


if __name__ == "__main__":
    main()
