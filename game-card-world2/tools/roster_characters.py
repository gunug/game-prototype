"""캐릭터 명단 — 사람과 크리처를 한 줄씩 적어 두고 한꺼번에 다시 뽑는다 (2026-10-06).

`make_character_sheet.py` (KREA2 체인 + BiRefNet-HR) 를 명단 순서대로 돌린다.
한 벌에 약 70초. 전부 돌리면 30~40분.

  python tools/roster_characters.py                 # 아직 얼굴 카드가 없는 것만
  python tools/roster_characters.py --all           # 전부 다시
  python tools/roster_characters.py --only wolf fox # 고른 것만

`--desc` 는 **그 캐릭터 묘사만** 적는다 — 그림체 · 틀 · 배경 문구는 스크립트가 붙인다.
크리처는 kind='creature' 라서 사람 · 인간형 · 손 · 옷 · 무기가 끼지 않게 못이 박히고,
전신은 왼쪽을 보게 그려진다 (docs/게임_규칙.md).
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET = Path(__file__).resolve().parent / "make_character_sheet.py"

# (파일 id, 한글 이름, 종류, 묘사)  — 파일 id 는 portrait_<id>.png 의 그 id
PEOPLE = [
    ("knight", "기사", "a young knight in worn leather and plate armor, short sword at his side, determined face"),
    ("innkeeper", "여관 주인", "a stout bearded innkeeper in a wool apron, one hand holding a clay mug, a cloth over the shoulder"),
    ("weaponsmith", "무기 장인", "a weathered weaponsmith in a thick leather apron, a stone-headed hammer resting on one shoulder"),
    ("cook", "요리사", "a camp cook in a soot-stained apron holding an iron skillet and a wooden ladle"),
    ("carpenter", "목수", "a carpenter with a hand saw in one hand and a plank under the other arm"),
    ("armorsmith", "갑옷 장인", "an armorer in heavy gloves holding a stitched leather cuirass at the hip"),
    ("shieldsmith", "방패 장인", "a shield maker holding a round wooden plank shield at his side, wood shavings on the boots"),
    ("trinketsmith", "장신구 장인", "a bead maker in a high-necked wool tunic, threading shell beads onto a cord"),
    ("herbalist", "약재 장인", "a hooded herbalist carrying a bundle of dried herbs and a clay jar"),
]
CREATURES = [
    ("animal", "토끼", "a wild brown rabbit standing alert on all fours, long ears up, small dark eyes"),
    ("wolf", "늑대", "a lean grey wolf, head lowered, teeth bared, bristling fur, yellow eyes, wild and dangerous"),
    ("bear", "곰", "a large brown bear on all fours, heavy shoulders and thick brown fur"),
    ("wilddog", "들개", "a lean wild steppe dog, shaggy tan and grey fur, ribs showing, bared teeth, ears pricked, bushy tail low"),
    ("boar", "멧돼지", "a stocky wild boar, bristly dark brown fur, short curved tusks, lowered head, angry"),
    ("bison", "들소", "a massive shaggy plains bison, broad shoulders, thick dark brown mane, short curved black horns, heavy hooves"),
    ("fox", "여우", "one single red fox, bushy tail low, alert ears"),
    ("wolfleader", "늑대 두목", "a large grey alpha wolf, scarred muzzle, thick mane, snarling"),
    ("forestbear", "숲곰", "a huge dark forest bear on four legs, green moss on its back fur, heavy and menacing"),
    ("stonebug", "돌벌레", "a beetle-like creature with a thick grey stone shell on its back, short legs"),
    ("shellback", "바위 등껍질", "a large armored creature whose back is a slab of grey rock, low and heavy"),
    ("stonelord", "돌가죽 주인", "a hulking beast covered in grey stone plates, glowing eyes under a rocky brow"),
    ("mosstoad", "이끼 두꺼비", "a huge swamp toad covered in green moss, warty wet skin, squatting low"),
    ("bogarm", "수렁 팔", "a monstrous long arm of mud and roots rising out of swamp water, clawed hand, dripping sludge"),
    ("tombkeeper", "무덤 주인", "a hulking swamp guardian beast made of waterlogged flesh, moss and grave stones, hunched, glowing pale eyes, dripping wet"),
    ("crayfish", "가재", "a big red river crayfish, raised pincers, segmented tail"),
    ("crocodile", "악어", "a crocodile, long toothy jaws, scaly green back, low stance"),
    ("catfish", "큰 메기", "a giant river catfish, long whiskers, wide mouth, dark slick skin"),
    ("spider", "거미", "a hairy forest spider, eight long jointed legs, small dark eye cluster, bristled abdomen"),
    ("webmother", "거미 어미", "a huge bloated spider matriarch, pale swollen abdomen marked with dark patterns, thick bristled legs, trailing silk strands"),
    ("nestkeeper", "둥지 주인", "a massive armored spider lord, spiny black carapace with bone-like plates, barbed legs, small red eye cluster, draped in torn webbing"),
    ("hermit", "소라게", "a hermit crab wearing a spiral seashell as its home, one big claw raised, wet rocky look"),
    ("bigpincer", "큰 집게", "a large armored crab with one oversized pincer and a thick barnacle-crusted shell"),
    ("cavekeeper", "동굴 주인", "a giant armored sea crustacean lord with a massive layered shell, heavy pincers and small glowing eyes, dripping wet"),
    ("towereye", "탑의 눈", "a huge single glowing eye embedded in cracked broken stone masonry, carved rock eyelids, pale light beams from the pupil, ancient unmoving stone"),
]
# 얼굴을 찾는 말 — 사람은 face, 짐승은 head. 얼굴이랄 것이 없는 것은 따로 적는다
SEG = {"bogarm": "hand", "towereye": "eye", "catfish": "fish head", "crayfish": "head"}
# 얼굴이랄 것이 없어 얼굴 검출이 빗나가는 것들 — 카드는 **전신 그림**으로 뜬다 (통째로 담아야 64px 에서 읽힌다)
CARD_FROM_FULL = {"bison", "forestbear", "stonebug", "shellback", "stonelord", "spider", "webmother", "hermit"}


def rows(args):
    all_rows = [(i, n, "person", d, 170) for i, n, d in PEOPLE] + \
               [(i, n, "creature", d, 260) for i, n, d in CREATURES]   # 짐승 머리는 더 넓게 잡아야 귀·주둥이가 다 담긴다
    if args.only:
        pick = set(args.only)
        all_rows = [r for r in all_rows if r[0] in pick]
        missing = pick - {r[0] for r in all_rows}
        if missing:
            sys.exit(f"명단에 없음: {sorted(missing)}")
    if not args.all and not args.only:                            # 아직 얼굴 카드가 없는 것만
        all_rows = [r for r in all_rows if not (ROOT / "images" / "icon" / f"card_{r[0]}.png").exists()]
    return all_rows


def main():
    ap = argparse.ArgumentParser(description="명단대로 캐릭터 시트를 한꺼번에 뽑는다")
    ap.add_argument("--all", action="store_true", help="이미 있는 것도 다시 뽑는다")
    ap.add_argument("--only", nargs="*", default=[], help="고른 id 만")
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()

    todo = rows(a)
    print(f"{len(todo)} 벌 — 한 벌 약 70초\n")
    fail = []
    t0 = time.time()
    for n, (cid, label, kind, desc, face_pad) in enumerate(todo, 1):
        print(f"\n===== [{n}/{len(todo)}] {cid} ({label}) =====")
        cmd = [sys.executable, str(SHEET), "--name", cid, "--kind", kind, "--label", label,
               "--desc", desc, "--face-pad", str(face_pad), "--force", "--url", a.url]
        cmd += ["--seg-text", SEG.get(cid, "face" if kind == "person" else "head")]
        if cid in CARD_FROM_FULL:
            cmd += ["--card-from", "full"]
        r = subprocess.run(cmd, cwd=str(ROOT))
        if r.returncode:
            fail.append(cid)
            print(f"!! 실패: {cid}")
    print(f"\n끝 — {len(todo) - len(fail)}/{len(todo)} 성공 · {(time.time() - t0) / 60:.1f}분")
    if fail:
        print("실패: " + ", ".join(fail))
        sys.exit(1)


if __name__ == "__main__":
    main()
