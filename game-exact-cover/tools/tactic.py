"""묘수풀이 필드 생성기 — 작은데 반박이 깊은 문제를 찾는다.

일반 스테이지(generate.py)는 "칸 수와 조밀도를 정해 놓고 CP-SAT 로 필드를
만든다". 그 방식은 반박 깊이를 겨냥할 수가 없다. 깊이는 풀이 과정의 성질이라
제약으로 못 쓰기 때문이다.

그래서 여기서는 반대로 간다.

    조각을 실제로 깔아 필드를 만든다 (덮개가 있는 게 보장된다)
      -> 반박 깊이를 잰다
      -> 깊은 것만 남긴다

측정이 필드 하나에 수십 ms 라 수백 번 뽑아 고르는 편이 CP-SAT 보다 싸다.

깊게 만드는 조건은 실측으로 나왔다.

  - 조각이 작을수록 깊다. 큰 조각은 놓자마자 구멍이 나서 1수에 죽는다.
    L4 한 종 10조각 40칸이 최고 6수인데, L3 한 종 10조각 30칸은 9수가 나온다
  - 두 종이 더 깊다. 칸을 안 늘리고 후보만 늘린다. L3+L4 8조각 31칸에 9수
  - 조각 수는 깊이의 하한이다. k수를 엮으려면 최소 k조각은 있어야 한다

    python tools/tactic.py        # tools/stages-tactic.json 으로 굽는다
"""

import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate import COLS, ROWS, N, SHAPES, placements, rotations, connected, centered, to_bits
from measure import Puzzle

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "stages-tactic.json")

DEPTH_CAP = 8

TETS = ["T4", "L4", "J4"]
PENTOS = ["L5", "P5", "T5", "V5", "W5", "Y5"]
HEXES = ["P6", "V6", "Y6", "Z6"]

# 세 종 묶음. 조합이 폭발하므로 전부 돌리지 않고 골고루 겹치게 여섯 개만 고른다
PENTO_TRIPLES = [
    ["L5", "P5", "T5"], ["L5", "V5", "W5"], ["P5", "T5", "Y5"],
    ["T5", "V5", "W5"], ["L5", "P5", "Y5"], ["V5", "W5", "Y5"],
]
HEX_TRIPLES = [
    ["P6", "V6", "Y6"], ["P6", "V6", "Z6"],
    ["P6", "Y6", "Z6"], ["V6", "Y6", "Z6"],
]
MIXED_345 = [
    ["L3", "T4", "L5"], ["L3", "T4", "P5"], ["L3", "L4", "T5"],
    ["L3", "L4", "V5"], ["L3", "J4", "W5"], ["L3", "J4", "Y5"],
]
MIXED_456 = [
    ["T4", "L5", "P6"], ["T4", "P5", "V6"], ["L4", "T5", "Y6"],
    ["L4", "V5", "Z6"], ["J4", "W5", "P6"], ["J4", "Y5", "V6"],
]

# 소분류마다 (후보 조합, 조각 수 범위, 몇 번 깔아 볼지).
# 조각이 크면 같은 깊이를 내는 데 조각이 더 들고, 종이 늘면 배치가 많아져
# 깊이 재는 값이 비싸진다. 그래서 큰 묶음은 시도 횟수를 줄인다.
# 세 종은 모양마다 2조각 이상 써야 하므로 조각 수가 6 아래로는 못 내려간다.
CATEGORIES = [
    ("1종",      [["L3"]],                                        (8, 9, 10, 11), 100),
    ("3+4",      [["L3", "T4"], ["L3", "L4"], ["L3", "J4"]],      (7, 8, 9, 10), 100),
    ("4+5",      [[t, p] for t in TETS for p in PENTOS],          (7, 8, 9, 10), 60),
    ("5+6",      [[p, h] for p in PENTOS for h in HEXES],         (8, 9, 10), 60),
    ("4칸 3종",  [TETS],                                          (8, 9, 10, 11), 100),
    ("5칸 3종",  PENTO_TRIPLES,                                   (8, 9, 10), 60),
    # 6칸짜리는 놓자마자 구멍이 나서 1수에 죽기 쉽다. 깊은 게 드물어 더 뽑는다
    ("6칸 3종",  HEX_TRIPLES,                                     (8, 9, 10, 11), 200),
    ("3+4+5",    MIXED_345,                                       (8, 9, 10), 60),
    ("4+5+6",    MIXED_456,                                       (8, 9, 10), 50),
]

# 게임 규칙과 같이 회전형이 4개인 모양만 쓴다
for _cat, _combos, _counts, _trials in CATEGORIES:
    for _names in _combos:
        for _n in _names:
            assert len(rotations(SHAPES[_n])) == 4, f"{_n} 은 회전형이 4개가 아니다"

PICK = 3             # 소분류마다 몇 문제


# ── 필드 만들기 ─────────────────────────────────────────────────────────


def _touch(cells_set, piece):
    for c in piece:
        r, co = divmod(c, COLS)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, co + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and nr * COLS + nc in cells_set:
                return True
    return False


def grow(names, npieces, rnd, min_each=2):
    """
    조각을 실제로 이어 붙여 필드를 만든다.

    이렇게 만들면 덮개가 하나 이상 있는 게 보장된다. 무작위로 칸을 골라 놓고
    풀리는지 확인하는 방식은 대부분 버려져서 훨씬 비싸다.
    두 종이면 모양마다 min_each 조각 이상 쓰게 해 한쪽만으로 덮는 답을 막는다.
    """
    pools = [[set(p) for p in placements(SHAPES[n])] for n in names]
    cells = set()
    used = [0] * len(names)

    order = []
    for si in range(len(names)):
        order += [si] * min_each
    rest = npieces - len(order)
    if rest < 0:
        return None
    order += [rnd.randrange(len(names)) for _ in range(rest)]
    rnd.shuffle(order)

    for si in order:
        pool = pools[si]
        for _ in range(400):
            p = rnd.choice(pool)
            if p & cells:
                continue
            if cells and not _touch(cells, p):
                continue
            cells |= p
            used[si] += 1
            break
        else:
            return None
    return cells if all(u >= min_each or len(names) == 1 for u in used) else cells


# ── 한 후보 재기 ────────────────────────────────────────────────────────


def adjacency(cells):
    """붙어 있는 칸 쌍의 수. 클수록 뭉툭해서 보기에도 낫다."""
    n = 0
    for c in cells:
        r, co = divmod(c, COLS)
        if co + 1 < COLS and r * COLS + co + 1 in cells:
            n += 1
        if r + 1 < ROWS and (r + 1) * COLS + co in cells:
            n += 1
    return n


def probe(job):
    """(조합, 조각 수) 하나를 여러 번 뽑아 가장 깊은 것들을 돌려준다."""
    cat, names, npieces, seed, trials = job
    rnd = random.Random(seed)
    best = []
    for _ in range(trials):
        cells = grow(names, npieces, rnd)
        if not cells or not connected(cells):
            continue
        # 재기 전에 먼저 판 가운데로 옮긴다. 깊이 탐색이 "읽는 순서로 가장 앞선
        # 빈 칸" 에서 갈라지므로, 필드를 옮기면 그 순서가 바뀌어 깊이도 달라진다.
        # 옮기기 전 값으로 골라 놓고 옮긴 필드를 내보내면 값이 어긋난다
        cells = centered(cells)
        pz = Puzzle(names, to_bits(cells))
        if not pz.feasible():
            continue
        rd = pz.refute_depth(cap=DEPTH_CAP)
        best.append({
            "cat": cat,
            "shapes": names,
            "pieces": npieces,
            "cells": len(cells),
            "depth": rd["depth"],
            "adj": adjacency(cells),
            "field": to_bits(cells),
        })
    best.sort(key=lambda r: (-r["depth"], r["cells"], -r["adj"]))
    return best[:8]


def main():
    jobs = []
    for cat, combos, counts, trials in CATEGORIES:
        for ci, names in enumerate(combos):
            for pi, npieces in enumerate(counts):
                if npieces < 2 * len(names):
                    continue        # 모양마다 2조각씩은 써야 한다
                jobs.append((cat, names, npieces, 9000 + ci * 131 + pi * 17, trials))

    workers = min(os.cpu_count() or 4, 12)
    print(f"후보 {len(jobs)}묶음, 프로세스 {workers}개", file=sys.stderr)

    pool_out = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, res in enumerate(pool.map(probe, jobs)):
            pool_out += res
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(jobs)}", file=sys.stderr)

    out = []
    for cat, _combos, _counts, _trials in CATEGORIES:
        rows = [r for r in pool_out if r["cat"] == cat]
        # 조각 수가 깊이에 붙어 있으면 "반박" 이 아니라 그냥 끝까지 푸는 것이다.
        # 여유를 두 조각 이상 남긴 것만 묘수로 친다
        real = [r for r in rows if r["pieces"] >= r["depth"] + 2] or rows
        real.sort(key=lambda r: (-r["depth"], r["pieces"], r["cells"], -r["adj"]))

        # 같은 조합만 몰아 뽑지 않게 한 조합당 둘까지. 조합이 하나뿐인 소분류
        # (1종은 3칸짜리 4회전 모양이 L3 하나뿐이다) 나 후보가 모자라면
        # 두 번째 훑기에서 그 제한을 푼다
        picked, seen_field, seen_combo = [], set(), {}
        for cap_per_combo in (2, PICK):
            for r in real:
                if len(picked) == PICK:
                    break
                if r["field"] in seen_field:
                    continue
                key = "+".join(r["shapes"])
                if seen_combo.get(key, 0) >= cap_per_combo:
                    continue
                seen_field.add(r["field"])
                seen_combo[key] = seen_combo.get(key, 0) + 1
                picked.append(r)
            if len(picked) == PICK:
                break

        for r in picked:
            out.append({
                "name": "+".join(r["shapes"]) + f" {r['cells']}칸 묘수",
                "mode": "tactic",
                "tactic": cat,
                "shapes": r["shapes"],
                "cells": r["cells"],
                "pieces": r["pieces"],
                "field": r["field"],
            })
            print(f"  [{cat}] {'+'.join(r['shapes']):8} {r['pieces']:2}조각 "
                  f"{r['cells']:3}칸  깊이 {r['depth']}", file=sys.stderr)
            for rr in range(ROWS):
                row = "".join("#" if r["field"][rr * COLS + c] == "1" else "."
                              for c in range(COLS))
                if "#" in row:
                    print("      " + row, file=sys.stderr)

    with open(DEST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"-> {DEST} ({len(out)}문제)", file=sys.stderr)


if __name__ == "__main__":
    main()
