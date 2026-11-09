"""사람 캐릭터 얼굴 · 상반신 · 전신을 **A포즈 시트 기준**으로 다시 뽑는다 (2026-11-09).

make_character_sheet.py --ref <시트 id> 를 사람마다 돌린다. 생김새(얼굴 · 머리 · 옷 · 비율)는
images/ref/apose_<id>.png 가 정하고, 글은 **손에 든 것 · 표정**만 적는다 (옷을 글로 적으면 시트와 싸운다).

  python tools/roster_ref.py               # 전부
  python tools/roster_ref.py --only knight archer
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET = Path(__file__).resolve().parent / "make_character_sheet.py"

# (파일 id, 시트 id, 한글, 글 속 이름, 손에 든 것 · 표정)
REF_PEOPLE = [
    ("knight", "knight", "가렛", "Garret", "a young knight, a plain short sword at his belt, a calm steady expression"),
    ("archer", "ally", "세리나", "Serina", "a cheerful young girl archer, holding a simple wooden bow, a bright confident smile"),
    ("innkeeper", "innkeeper", "보른", "Born", "a stout bearded innkeeper, one hand holding a clay mug, a cloth over the shoulder, a warm smile"),
    ("peddler", "peddler", "오르반", "Orban", "an old trader, a knowing calm smile, hands resting on his belt pouches"),
    ("weaponsmith", "weaponsmith", "두르간", "Durgan", "a broad weaponsmith, a stone-headed hammer resting on one shoulder, a gruff confident look"),
    ("cook", "cook", "올가", "Olga", "a plump cook woman, holding an iron skillet and a wooden ladle, a grumpy pursed mouth"),
    ("carpenter", "carpenter", "헤이든", "Hayden", "a lanky carpenter, a hand saw in one hand and a plank under the other arm, slightly nervous wide eyes"),
    ("armorsmith", "armorsmith", "마르그", "Marg", "a stern older woman armorer, a sewing needle tucked behind one ear, holding a stitched leather cuirass at the hip, thin pressed lips"),
    ("shieldsmith", "shieldsmith", "토른", "Thorn", "a big calm man, holding a round wooden plank shield at his side, steady eyes"),
    ("trinketsmith", "trinketsmith", "네이라", "Neira", "a young woman bead maker, threading shell beads onto a cord, a thin knowing smile"),
    ("herbalist", "herbalist", "실바", "Silva", "a wary young woman herbalist, carrying a bundle of dried herbs and a clay jar, a suspicious glare"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--url", default="http://127.0.0.1:8188")
    a = ap.parse_args()
    fail = []
    for cid, ref, label, nm, desc in REF_PEOPLE:
        if a.only and cid not in a.only:
            continue
        print(f"\n===== {cid} ({label}) =====", flush=True)
        r = subprocess.run([sys.executable, str(SHEET), "--name", cid, "--kind", "person", "--style", "deform",
                            "--label", label, "--desc", desc, "--ref", ref, "--ref-name", nm, "--face-pad", "170",
                            "--seed", str(a.seed), "--force", "--url", a.url], cwd=str(ROOT))
        if r.returncode:
            fail.append(cid)
    print("실패: " + ", ".join(fail) if fail else "끝 — 전부 성공")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
