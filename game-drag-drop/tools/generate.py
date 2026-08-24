"""스테이지 생성기 (OR-Tools CP-SAT 는 해 세는 데만 쓴다).

이 게임은 **회전이 없다**. 그래서 조각 하나는 "모양" 이 아니라 "방향까지 정해진
모양" 이다. 같은 L 라도 돌린 것은 서로 다른 조각으로 친다.

필드를 먼저 만들고 거기에 맞는 조각을 찾는 방식은 쓰지 않는다. 반대로

    조각을 실제로 이어 붙여 필드를 만든다
      -> 그 조각들이 곧 서랍 내용이다

이러면 풀리는 게 보장된다. 조각을 놓은 자리를 그대로 답으로 들고 있으니까.

    python tools/generate.py            # tools/stages.json 으로 굽는다
    python tools/generate.py --apply    # index.html 의 STAGES 까지 갱신
"""

import json
import os
import random
import sys

from ortools.sat.python import cp_model

COLS = ROWS = 10
N = COLS * ROWS

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, "..", "index.html")
DEST = os.path.join(HERE, "stages.json")

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def idx(c, r):
    return r * COLS + c


# ── 모양 ────────────────────────────────────────────────────────────────

SHAPES = {
    "I3": [(0, 0), (0, 1), (0, 2)],
    "L3": [(0, 0), (0, 1), (1, 1)],
    "I4": [(0, 0), (0, 1), (0, 2), (0, 3)],
    "O4": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T4": [(0, 0), (1, 0), (2, 0), (1, 1)],
    "L4": [(0, 0), (0, 1), (0, 2), (1, 2)],
    "S4": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z4": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "L5": [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3)],
    "P5": [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)],
    "T5": [(0, 0), (1, 0), (2, 0), (1, 1), (1, 2)],
    "U5": [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)],
    "V5": [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)],
    "W5": [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)],
    "Y5": [(1, 0), (0, 1), (1, 1), (1, 2), (1, 3)],
}


def normalize(cells):
    mc = min(c for c, _ in cells)
    mr = min(r for _, r in cells)
    return sorted((c - mc, r - mr) for c, r in cells)


def rotations(cells):
    out, cur = [], normalize(cells)
    for _ in range(4):
        out.append(cur)
        cur = normalize([(-r, c) for c, r in cur])
    return list({tuple(r): r for r in out}.values())


def oriented(names):
    """회전이 없으니 돌린 형태 하나하나가 따로 놀 조각이다."""
    out = []
    for n in names:
        for rot in rotations(SHAPES[n]):
            out.append(list(rot))
    return out


def cells_of(form, c0, r0):
    return [(c0 + c, r0 + r) for c, r in form]


# ── 필드 만들기 ─────────────────────────────────────────────────────────


def connected(cells):
    if not cells:
        return False
    start = next(iter(cells))
    seen, stack = {start}, [start]
    while stack:
        i = stack.pop()
        c, r = i % COLS, i // COLS
        for dc, dr in DIRS:
            nc, nr = c + dc, r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                j = idx(nc, nr)
                if j in cells and j not in seen:
                    seen.add(j)
                    stack.append(j)
    return len(seen) == len(cells)


def adjacency(cells):
    """붙어 있는 칸 쌍. 클수록 뭉툭하다."""
    n = 0
    for i in cells:
        c, r = i % COLS, i // COLS
        if c + 1 < COLS and idx(c + 1, r) in cells:
            n += 1
        if r + 1 < ROWS and idx(c, r + 1) in cells:
            n += 1
    return n


def touches(cells, ids):
    for i in ids:
        c, r = i % COLS, i // COLS
        for dc, dr in DIRS:
            nc, nr = c + dc, r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and idx(nc, nr) in cells:
                return True
    return False


def lay(forms, npieces, rnd):
    """조각을 이어 붙여 필드 하나를 만든다. 놓은 자리가 곧 답이다."""
    spots = []
    for form in forms:
        w = max(c for c, _ in form) + 1
        h = max(r for _, r in form) + 1
        for r0 in range(ROWS - h + 1):
            for c0 in range(COLS - w + 1):
                spots.append((form, [idx(c, r) for c, r in cells_of(form, c0, r0)]))

    cells, used = set(), []
    for _ in range(npieces):
        for _try in range(600):
            form, ids = rnd.choice(spots)
            if any(i in cells for i in ids):
                continue
            if cells and not touches(cells, ids):
                continue
            cells |= set(ids)
            used.append((form, ids))
            break
        else:
            return None
    return cells, used


def centered(cells, used):
    """판 가운데로 옮긴다. 안 그러면 한쪽 구석에 몰린다."""
    cs = [i % COLS for i in cells]
    rs = [i // COLS for i in cells]
    dc = (COLS - (max(cs) - min(cs) + 1)) // 2 - min(cs)
    dr = (ROWS - (max(rs) - min(rs) + 1)) // 2 - min(rs)

    def shift(i):
        return idx(i % COLS + dc, i // COLS + dr)

    return ({shift(i) for i in cells},
            [(form, [shift(i) for i in ids]) for form, ids in used])


# ── 해 세기 ─────────────────────────────────────────────────────────────


def count_solutions(cells, forms, cap=500):
    """
    서랍의 조각을 전부 써서 필드를 덮는 방법이 몇 가지인가.

    똑같이 생긴 조각은 서로 바꿔 놔도 같은 그림이라, 조각 하나하나가 아니라
    모양별 개수로 모델을 세운다. 안 그러면 같은 답이 개수만큼 부풀어 오른다.
    """
    kinds = {}
    for form in forms:
        key = tuple(map(tuple, form))
        kinds[key] = kinds.get(key, 0) + 1

    model = cp_model.CpModel()
    covering = {i: [] for i in cells}
    for form, count in kinds.items():
        w = max(c for c, _ in form) + 1
        h = max(r for _, r in form) + 1
        use = []
        for r0 in range(ROWS - h + 1):
            for c0 in range(COLS - w + 1):
                ids = [idx(c, r) for c, r in cells_of(form, c0, r0)]
                if any(i not in cells for i in ids):
                    continue
                v = model.NewBoolVar("")
                use.append(v)
                for i in ids:
                    covering[i].append(v)
        model.Add(sum(use) == count)
    for i in cells:
        model.Add(sum(covering[i]) == 1)

    class Counter(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__()
            self.n = 0

        def on_solution_callback(self):
            self.n += 1
            if self.n >= cap:
                self.StopSearch()

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = 20.0
    solver.parameters.num_workers = 1
    cb = Counter()
    solver.Solve(model, cb)
    return cb.n, cb.n >= cap


# ── 스테이지 커브 ───────────────────────────────────────────────────────

# (이름, 쓸 모양, 조각 수, 후보 수, 윤곽)
# 앞 스테이지는 뭉툭하고 조각도 적다. 뒤로 갈수록 조각이 늘고 윤곽이 사나워져
# 놓을 자리가 눈에 덜 들어온다.
CURVE = [
    ("첫 걸음",    ["O4", "L4", "T4"],                          5, 400, 1.00),
    ("네 칸",      ["L4", "T4", "S4", "Z4", "I4"],              7, 400, 1.00),
    ("섞기",       ["L3", "I3", "L4", "T4", "P5"],              9, 400, 0.92),
    ("펜토미노",   ["L5", "P5", "T5", "V5", "Y5"],             11, 400, 0.88),
    ("한 판 가득", ["L3", "T4", "S4", "L5", "W5", "U5", "Y5"], 13, 400, 0.85),
]


def build(names, npieces, tries, frac, seed):
    """
    여러 번 깔아 보고 조밀도 순위에서 frac 자리에 있는 것을 고른다.

    가장 뭉툭한 것만 뽑으면 어느 스테이지나 비슷한 덩어리가 되고, 가장 사나운
    것을 뽑으면 폭 1칸짜리 촉수가 뻗어 나와 보기에도 풀기에도 나쁘다.
    1.0 이 가장 뭉툭, 0.8 쯤이 윤곽에 요철이 남는 정도다.
    """
    forms = oriented(names)
    rnd = random.Random(seed)
    seen, cand = set(), []
    for _ in range(tries):
        got = lay(forms, npieces, rnd)
        if not got:
            continue
        cells, used = got
        if not connected(cells):
            continue
        key = frozenset(cells)
        if key in seen:
            continue
        seen.add(key)
        cand.append((adjacency(cells), cells, used))
    if not cand:
        return None
    cand.sort(key=lambda x: x[0])
    return cand[round(frac * (len(cand) - 1))]


def main():
    out = []
    for si, (name, names, npieces, tries, frac) in enumerate(CURVE):
        best = build(names, npieces, tries, frac, 100 + si * 7)
        if not best:
            print(f"{name}: 생성 실패", file=sys.stderr)
            continue
        cells, used = centered(best[1], best[2])

        # 서랍 순서를 놓은 순서 그대로 두면 답이 새어 나간다. 섞는다
        rnd = random.Random(500 + si)
        forms = [form for form, _ids in used]
        rnd.shuffle(forms)

        sols, capped = count_solutions(cells, forms)
        out.append({
            "name": name,
            "cells": len(cells),
            "pieces": [[[c, r] for c, r in form] for form in forms],
            "solutions": sols,
            "capped": capped,
            "field": "".join("1" if i in cells else "0" for i in range(N)),
        })
        print(f"  {name}: {len(cells)}칸 {len(forms)}조각, "
              f"해 {sols}{'+' if capped else ''}", file=sys.stderr)
        for r in range(ROWS):
            row = "".join("#" if idx(c, r) in cells else "." for c in range(COLS))
            if "#" in row:
                print("    " + row, file=sys.stderr)

    with open(DEST, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"-> {DEST}", file=sys.stderr)

    if "--apply" in sys.argv:
        apply_to_game(out)
        print("index.html 갱신함", file=sys.stderr)


def emit(stages):
    lines = [
        "  /* ==================== 스테이지 ==================== */",
        "",
        "  /**",
        "   * tools/generate.py 가 조각을 실제로 깔아 만든 값이다. 깔아서 만들었으니",
        "   * 답이 반드시 하나 이상 있다. field 는 좌상단부터 행 우선으로 읽는",
        "   * 10x10 비트맵, pieces 는 회전 없이 그대로 놓아야 할 조각들이다.",
        "   */",
        "  const STAGES = [",
    ]
    for st in stages:
        pieces = ", ".join(
            "[" + ", ".join(f"[{c},{r}]" for c, r in p) + "]" for p in st["pieces"])
        lines += [
            "    {",
            f"      name: '{st['name']}',",
            f"      // {st['cells']}칸 | 조각 {len(st['pieces'])}개 | "
            f"해 {st['solutions']}{'+' if st['capped'] else ''}",
            f"      pieces: [{pieces}],",
            f"      field: '{st['field']}',",
            "    },",
        ]
    lines += [
        "  ];",
        "",
        "  /** 비트맵 문자열 -> 채워야 할 칸 번호 집합 */",
        "  function readField(bits) {",
        "    const out = new Set();",
        "    for (let i = 0; i < bits.length; i++) if (bits[i] === '1') out.add(i);",
        "    return out;",
        "  }",
        "",
    ]
    return "\n".join(lines)


def apply_to_game(stages):
    html = open(GAME, encoding="utf-8").read()
    head = "  /* ==================== 스테이지 ==================== */"
    tail = "  /* ==================== 상태 ==================== */"
    start, end = html.index(head), html.index(tail)
    open(GAME, "w", encoding="utf-8").write(html[:start] + emit(stages) + html[end:])


if __name__ == "__main__":
    main()
