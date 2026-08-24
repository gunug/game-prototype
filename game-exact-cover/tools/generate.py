"""스테이지 필드 생성기 (OR-Tools CP-SAT).

정확한 덮개를 제약으로 직접 걸어 필드를 만든다. 무작위로 깔아 놓고 걸러내는
방식과 달리, 원하는 모양 조건을 선언하면 솔버가 그 조건을 만족하는 필드를
찾아 준다. 특히 뚱뚱한(둘레가 짧은) 필드는 탐욕적 성장으로는 아예 만들 수
없었는데, 여기서는 목적함수 한 줄이면 된다.

    python tools/generate.py [출력경로]

기본 출력은 tools/stages.json. ortools 가 stdout 에 DLL 적재 로그를 찍기
때문에 파이프가 아니라 파일로 쓴다. 이 JSON 을 index.html 의 STAGES 에
넣는다. 게임은 생성을 하지 않고 구워진 필드를 그대로 읽는다.
"""

import json
import os
import random
import sys

from ortools.sat.python import cp_model

COLS = ROWS = 10
N = COLS * ROWS

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))


def idx(c, r):
    return r * COLS + c


# ── 모양 ────────────────────────────────────────────────────────────────

SHAPES = {
    # 트로미노
    "I3": [(0, 0), (0, 1), (0, 2)],
    "L3": [(0, 0), (0, 1), (1, 1)],
    # 테트로미노
    "I4": [(0, 0), (0, 1), (0, 2), (0, 3)],
    "O4": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T4": [(0, 0), (1, 0), (2, 0), (1, 1)],
    "L4": [(0, 0), (0, 1), (0, 2), (1, 2)],
    # L4 의 거울상. 반사는 다른 모양으로 보므로 4회전 테트로미노는 T4 L4 J4 셋이다
    "J4": [(0, 0), (0, 1), (0, 2), (1, 0)],
    "S4": [(1, 0), (2, 0), (0, 1), (1, 1)],
    # 펜토미노
    "L5": [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3)],
    "P5": [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)],
    "T5": [(0, 0), (1, 0), (2, 0), (1, 1), (1, 2)],
    "V5": [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)],
    "W5": [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)],
    "Y5": [(1, 0), (0, 1), (1, 1), (1, 2), (1, 3)],
    # 헥소미노 — 묘수풀이의 5칸+6칸 묶음에 쓴다. 회전형 4개짜리만 골랐다
    "P6": [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (0, 3)],
    "V6": [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (0, 3)],
    "Y6": [(2, 0), (2, 1), (0, 2), (1, 2), (2, 2), (3, 2)],
    "Z6": [(1, 0), (2, 0), (0, 1), (1, 1), (1, 2), (2, 2)],
}


def normalize(cells):
    mc = min(c for c, _ in cells)
    mr = min(r for _, r in cells)
    return sorted((c - mc, r - mr) for c, r in cells)


def rotations(cells):
    """0/90/180/270 회전형. 반사는 다른 모양으로 본다 (게임 규칙과 같음)."""
    out, cur = [], normalize(cells)
    for _ in range(4):
        out.append(cur)
        cur = normalize([(-r, c) for c, r in cur])
    # 대칭인 모양은 같은 회전형이 겹치므로 중복 제거
    uniq = {tuple(r): r for r in out}
    return list(uniq.values())


def placements(shape):
    """10x10 안에 들어가는 모든 배치를 칸 번호 집합으로."""
    out, seen = [], set()
    for rot in rotations(shape):
        w = max(c for c, _ in rot) + 1
        h = max(r for _, r in rot) + 1
        for r0 in range(ROWS - h + 1):
            for c0 in range(COLS - w + 1):
                ids = tuple(sorted(idx(c0 + c, r0 + r) for c, r in rot))
                if ids in seen:
                    continue
                seen.add(ids)
                out.append(ids)
    return out


# ── 모델 ────────────────────────────────────────────────────────────────


def _model(shape_names, cells_total, min_each=0):
    """
    정확한 덮개 제약만 세운 모델. 목적함수는 부르는 쪽에서 얹는다.

    모양이 둘 이상이면 크기가 달라 조각 수로는 칸 수가 정해지지 않으므로,
    조각 수 대신 칸 수를 고정한다. min_each 는 모양마다 최소 몇 조각을 쓸지로,
    한쪽 모양만 써서 덮어 버리는 답을 막는다.
    """
    model = cp_model.CpModel()
    active = [model.NewBoolVar(f"a{i}") for i in range(N)]

    covering = [[] for _ in range(N)]
    per_shape = []
    for si, name in enumerate(shape_names):
        places = placements(SHAPES[name])
        use = [model.NewBoolVar(f"p{si}_{i}") for i in range(len(places))]
        per_shape.append(use)
        for v, cells in zip(use, places):
            for cell in cells:
                covering[cell].append(v)

    # 각 칸은 정확히 한 조각에 덮이거나, 필드가 아니거나
    for cell in range(N):
        model.Add(sum(covering[cell]) == active[cell])

    model.Add(sum(active) == cells_total)
    if min_each and len(shape_names) > 1:
        for use in per_shape:
            model.Add(sum(use) >= min_each)

    # 붙어 있는 활성 칸 쌍의 수. 칸 수가 고정이라 이걸 키우면 둘레가 줄어든다
    adj = []
    for r in range(ROWS):
        for c in range(COLS):
            for dc, dr in ((1, 0), (0, 1)):
                nc, nr = c + dc, r + dr
                if nc >= COLS or nr >= ROWS:
                    continue
                a, b = active[idx(c, r)], active[idx(nc, nr)]
                t = model.NewBoolVar("")
                model.AddBoolAnd([a, b]).OnlyEnforceIf(t)
                model.AddBoolOr([a.Not(), b.Not()]).OnlyEnforceIf(t.Not())
                adj.append(t)

    return model, active, adj


def _solve(model, seed, time_limit):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    ok = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    return (solver, status) if ok else (None, status)


def build(shape_names, cells_total, seed, frac=0.7, time_limit=30.0, min_each=2):
    """
    정확히 덮이는 필드를 하나 만든다.

    frac 은 조밀도. 0 이면 한 줄로 늘어선 최소 인접쌍, 1 이면 둘레가 가장
    짧은 뭉치(대개 직사각형)다. 둘레만 최소화하면 매번 같은 직사각형이 나와서,
    목표 조밀도를 하한으로 걸고 그 안에서 무작위로 고른다.
    """
    if isinstance(shape_names, str):
        shape_names = [shape_names]
    n = cells_total

    # 1) 이 칸 수로 가능한 최대 인접쌍 = 조밀도의 위쪽 끝
    model, active, adj = _model(shape_names, n, min_each)
    model.Maximize(sum(adj))
    solver, status = _solve(model, seed, time_limit)
    if solver is None:
        return None
    adj_max = int(solver.ObjectiveValue())

    # 2) 한 덩어리로 이어지려면 최소 n-1 쌍. 그 사이를 frac 으로 자른다
    target = round((n - 1) + frac * (adj_max - (n - 1)))

    model, active, adj = _model(shape_names, n, min_each)
    model.Add(sum(adj) >= target)
    rnd = random.Random(seed)
    jitter = [rnd.randrange(0, 64) for _ in range(N)]
    model.Maximize(sum(w * a for w, a in zip(jitter, active)))

    solver, status = _solve(model, seed, time_limit)
    if solver is None:
        return None

    cells = {i for i in range(N) if solver.Value(active[i])}
    return {
        "cells": cells,
        "adjacent": sum(1 for t in adj if solver.Value(t)),
        "adj_max": adj_max,
        "target": target,
        "optimal": status == cp_model.OPTIMAL,
    }


# ── 후처리 ──────────────────────────────────────────────────────────────


def connected(cells):
    """한 덩어리인지. 둘레를 줄이면 대개 붙지만 보장은 아니라서 확인한다."""
    if not cells:
        return False
    seen, stack = {next(iter(cells))}, [next(iter(cells))]
    while stack:
        i = stack.pop()
        c, r = i % COLS, i // COLS
        for dc, dr in DIRS:
            nc, nr = c + dc, r + dr
            if not (0 <= nc < COLS and 0 <= nr < ROWS):
                continue
            j = idx(nc, nr)
            if j in cells and j not in seen:
                seen.add(j)
                stack.append(j)
    return len(seen) == len(cells)


def centered(cells):
    """판 가운데로 옮긴다. 솔버는 위치를 신경 쓰지 않아 한쪽에 몰릴 수 있다."""
    cs = [i % COLS for i in cells]
    rs = [i // COLS for i in cells]
    dc = (COLS - (max(cs) - min(cs) + 1)) // 2 - min(cs)
    dr = (ROWS - (max(rs) - min(rs) + 1)) // 2 - min(rs)
    return {idx(i % COLS + dc, i // COLS + dr) for i in cells}


def to_bits(cells):
    return "".join("1" if i in cells else "0" for i in range(N))


# ── 스테이지 목록 ───────────────────────────────────────────────────────

# 조각 수와 조밀도를 바꿔 가며 모양마다 여러 문제를 뽑는다.
# 조밀도를 1.0 으로 두면 매번 직사각형이 나온다. 0.55~0.85 대가 뭉툭하면서도
# 윤곽에 요철이 남아 문제마다 다르게 생긴다.
FRACS = (0.55, 0.70, 0.85)

# 회전형이 4개인 모양만 쓴다. 정사각(O4)은 1개, 막대와 번개(I3 I4 S4)는 2개라
# 놓을 자리가 적어 그대로 강제로 굳는다 — 60칸에서 O4 배치 38개, L4 는 124개다.
FAMILIES = [
    (["L3"], (8, 12, 16)),                              # 트로미노
    (["T4", "L4"], (9, 12, 15)),                        # 테트로미노
    (["L5", "P5", "T5", "V5", "W5", "Y5"], (10, 13, 16)),  # 펜토미노
]


def single_curve():
    out = []
    for shapes, counts in FAMILIES:
        for name in shapes:
            size = len(SHAPES[name])
            for i, pieces in enumerate(counts):
                out.append(([name], pieces * size, FRACS[i % len(FRACS)]))
    return out


# 두 종을 섞는 문제. 같은 크기끼리도, 크기가 다른 것끼리도 섞는다
DUAL_CURVE = [
    (["L3", "T4"], 60, 0.70),
    (["L3", "L4"], 66, 0.75),
    (["T4", "L4"], 64, 0.80),
    (["L3", "L5"], 65, 0.75),
    (["T4", "L5"], 72, 0.80),
    (["T4", "P5"], 72, 0.80),
    (["L4", "T5"], 76, 0.80),
    (["L4", "W5"], 76, 0.85),
    (["L5", "T5"], 80, 0.85),
    (["P5", "V5"], 80, 0.85),
]

# 앞으로 4회전 모양만 다루기로 했으니 커브가 그걸 지키는지 확인한다
for _names, _cells, _frac in single_curve() + DUAL_CURVE:
    for _n in _names:
        assert len(rotations(SHAPES[_n])) == 4, f"{_n} 은 회전형이 4개가 아니다"


CURVE = single_curve()


# ── 검증 ────────────────────────────────────────────────────────────────


def verify():
    """index.html 에 구워 넣은 필드가 정말 그 모양으로 덮이는지 다시 푼다."""
    import re

    here = os.path.dirname(os.path.abspath(__file__))
    html = io_open(os.path.join(here, "..", "index.html"))

    entries = re.findall(
        r"id: '([^']+)',.*?shapes: \[([^\]]+)\],.*?field: '([01]+)'",
        html, re.S)
    if not entries:
        print("STAGES 를 못 읽음", file=sys.stderr)
        return 1

    bad = 0
    for name, shape_src, bits in entries:
        names = re.findall(r"SHAPES\.(\w+)", shape_src)
        cells = {i for i, ch in enumerate(bits) if ch == "1"}
        sizes = [len(SHAPES[n]) for n in names]
        # 한 종이면 칸 수가 조각 크기의 배수여야 한다. 두 종은 섞이므로 안 따진다
        ok_size = len(cells) % sizes[0] == 0 if len(names) == 1 else True
        ok_conn = connected(cells)

        # 이 칸들만 정확히 덮는 해가 있는지. 두 종이면 둘 다 최소 하나씩 써야 한다
        model = cp_model.CpModel()
        covering = {c: [] for c in cells}
        per_shape = []
        for n in names:
            places = [p for p in placements(SHAPES[n]) if set(p) <= cells]
            use = [model.NewBoolVar("") for _ in places]
            per_shape.append(use)
            for v, p in zip(use, places):
                for c in p:
                    covering[c].append(v)
        for c in cells:
            model.Add(sum(covering[c]) == 1)
        if len(names) > 1:
            for use in per_shape:
                model.Add(sum(use) >= 1)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        ok_cover = solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        mark = "OK " if (ok_size and ok_conn and ok_cover) else "실패"
        if mark != "OK ":
            bad += 1
        print(f"  {mark} {name}: {'+'.join(names)} {len(cells)}칸 "
              f"배수 {ok_size} 연결 {ok_conn} 덮개 {ok_cover}", file=sys.stderr)
    return 1 if bad else 0


def io_open(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    dual = "--dual" in sys.argv
    curve = DUAL_CURVE if dual else CURVE
    mode = "dual" if dual else "single"

    out = []
    for i, (shape_names, cells_total, frac) in enumerate(curve):
        name = "+".join(shape_names) + f" {cells_total}칸 f{frac}"
        result = None
        for attempt in range(6):
            seed = 1000 + i * 37 + attempt
            r = build(shape_names, cells_total, seed, frac)
            if r and connected(r["cells"]):
                result = r
                break
            print(f"  {name}: 시드 {seed} 실패, 재시도", file=sys.stderr)
        if not result:
            print(f"{name}: 생성 실패", file=sys.stderr)
            continue

        cells = centered(result["cells"])
        out.append({
            "name": name,
            "mode": mode,
            "shapes": list(shape_names),
            "cells": len(cells),
            "adjacent": result["adjacent"],
            "adjMax": result["adj_max"],
            "frac": frac,
            "optimal": result["optimal"],
            "field": to_bits(cells),
        })
        print(
            f"  {name}: {len(cells)}칸, "
            f"인접쌍 {result['adjacent']}/{result['adj_max']} (목표 {result['target']}), "
            f"{'최적' if result['optimal'] else '시간초과'}",
            file=sys.stderr,
        )
        for r in range(ROWS):
            row = "".join("#" if idx(c, r) in cells else "." for c in range(COLS))
            print("    " + row, file=sys.stderr)

    default = "stages-dual.json" if dual else "stages.json"
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dest = args[0] if args else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), default)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"-> {dest}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(verify() if "--verify" in sys.argv else (main() or 0))
