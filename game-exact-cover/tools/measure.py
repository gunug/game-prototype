"""스테이지 난이도 측정기 (OR-Tools CP-SAT).

generate.py 가 만든 필드를 읽어 난이도를 재고, 1~100 점수를 매겨 쉬운 것부터
정렬한 뒤 index.html 의 STAGES 를 다시 쓴다.

    python tools/measure.py            # 재기만 하고 표로 보여줌
    python tools/measure.py --apply    # index.html 의 STAGES 까지 갱신

솔버가 그냥 뱉는 num_conflicts / num_branches 는 쓰지 않는다. CP-SAT 전처리가
정확한 덮개에 워낙 강해서 사람이 헤매는 문제도 충돌 0 으로 끝나 변별력이 없다.
대신 "사람이 저지를 법한 상황"을 만들어 놓고 솔버에게 물어보는 값을 쓴다.
"""

import json
import os
import random
import re
import sys
from concurrent.futures import ProcessPoolExecutor

from ortools.sat.python import cp_model

from generate import COLS, ROWS, SHAPES, placements, idx

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, "..", "index.html")
SOURCES = [
    (os.path.join(HERE, "stages.json"), "single"),
    (os.path.join(HERE, "stages-dual.json"), "dual"),
]
MEASURED = os.path.join(HERE, "measured.json")

SHAPE_LABEL = {
    "I3": "트로미노 I", "L3": "트로미노 L",
    "I4": "테트로미노 I", "O4": "테트로미노 O", "T4": "테트로미노 T",
    "L4": "테트로미노 L", "S4": "테트로미노 S",
    "L5": "펜토미노 L", "P5": "펜토미노 P", "T5": "펜토미노 T",
    "V5": "펜토미노 V", "W5": "펜토미노 W", "Y5": "펜토미노 Y",
}

SHAPE_SRC = {
    "I3": "[[0, 0], [0, 1], [0, 2]]",
    "L3": "[[0, 0], [0, 1], [1, 1]]",
    "I4": "[[0, 0], [0, 1], [0, 2], [0, 3]]",
    "O4": "[[0, 0], [1, 0], [0, 1], [1, 1]]",
    "T4": "[[0, 0], [1, 0], [2, 0], [1, 1]]",
    "L4": "[[0, 0], [0, 1], [0, 2], [1, 2]]",
    "S4": "[[1, 0], [2, 0], [0, 1], [1, 1]]",
    "L5": "[[0, 0], [0, 1], [0, 2], [0, 3], [1, 3]]",
    "P5": "[[0, 0], [1, 0], [0, 1], [1, 1], [0, 2]]",
    "T5": "[[0, 0], [1, 0], [2, 0], [1, 1], [1, 2]]",
    "V5": "[[0, 0], [0, 1], [0, 2], [1, 2], [2, 2]]",
    "W5": "[[0, 0], [0, 1], [1, 1], [1, 2], [2, 2]]",
    "Y5": "[[1, 0], [0, 1], [1, 1], [1, 2], [1, 3]]",
}


# ── 한 스테이지를 다루는 도구 ───────────────────────────────────────────


class Puzzle:
    def __init__(self, shape_names, bits):
        if isinstance(shape_names, str):
            shape_names = [shape_names]
        self.shape_names = list(shape_names)
        self.shapes = [SHAPES[n] for n in self.shape_names]
        self.sizes = [len(sh) for sh in self.shapes]
        self.size = max(self.sizes)
        self.cells = frozenset(i for i, ch in enumerate(bits) if ch == "1")
        # 필드 안에 온전히 들어가는 배치만 남긴다. 모양이 둘이면 둘 다 모은다
        self.places = []
        for sh in self.shapes:
            self.places += [p for p in placements(sh) if set(p) <= self.cells]
        # 조각 크기가 다르면 조각 수가 고정이 아니라서 평균으로 잡는다
        self.pieces = max(1, round(len(self.cells) / (sum(self.sizes) / len(self.sizes))))
        self.det_time = 0.0

    def _model(self):
        """각 칸이 정확히 한 조각에 덮이는 모델."""
        m = cp_model.CpModel()
        use = [m.NewBoolVar(f"u{i}") for i in range(len(self.places))]
        covering = {c: [] for c in self.cells}
        for v, p in zip(use, self.places):
            for c in p:
                covering[c].append(v)
        for c in self.cells:
            m.Add(sum(covering[c]) == 1)
        return m, use

    # 모델이 아주 작아서 솔버를 병렬로 돌리면 이득보다 준비 비용이 크다.
    # 대신 스테이지 단위로 프로세스를 나눈다.
    def _solve(self, m, limit=5.0, workers=1):
        s = cp_model.CpSolver()
        s.parameters.max_time_in_seconds = limit
        s.parameters.num_workers = workers
        st = s.Solve(m)
        # deterministic_time 은 기계와 무관해서 실행마다 같은 값이 나온다
        self.det_time += s.ResponseProto().deterministic_time
        return s, st

    # ── 기본 질의 ──

    def solve_one(self, fixed=(), banned=()):
        m, use = self._model()
        for i in fixed:
            m.Add(use[i] == 1)
        for i in banned:
            m.Add(use[i] == 0)
        s, st = self._solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        return [i for i, v in enumerate(use) if s.Value(v)]

    def feasible(self, fixed=(), banned=()):
        return self.solve_one(fixed, banned) is not None

    # ── 지표 ──

    def count_solutions(self, cap=5000, limit=20.0):
        """해의 개수. 상한에 걸리면 (cap, True)."""
        m, _ = self._model()

        class Counter(cp_model.CpSolverSolutionCallback):
            def __init__(self):
                super().__init__()
                self.n = 0

            def on_solution_callback(self):
                self.n += 1
                if self.n >= cap:
                    self.StopSearch()

        s = cp_model.CpSolver()
        s.parameters.enumerate_all_solutions = True
        s.parameters.max_time_in_seconds = limit
        s.parameters.num_workers = 1     # 전수 열거는 병렬 이득이 거의 없다
        cb = Counter()
        s.Solve(m, cb)
        self.det_time += s.ResponseProto().deterministic_time
        return cb.n, cb.n >= cap

    def forced_ratio(self, rounds=4):
        """
        추측 없이 확정되는 조각의 비율.

        배치 p 를 금지하고 풀어서 불가능하면 p 는 모든 해에 들어간다 = 강제.
        확정된 것을 고정하고 다시 돌리면 연쇄 추론이 된다.
        """
        fixed, covered = [], set()
        for _ in range(rounds):
            gained = False
            for i, p in enumerate(self.places):
                if i in fixed or (covered & set(p)):
                    continue
                if not self.feasible(fixed=fixed, banned=[i]):
                    fixed.append(i)
                    covered |= set(p)
                    gained = True
            if not gained:
                break
        return len(covered) / len(self.cells), len(fixed)

    def min_swap(self):
        """다른 해가 되려면 조각을 최소 몇 개 갈아야 하는가. 유일해면 None."""
        base = self.solve_one()
        if base is None:
            return None
        m, use = self._model()
        m.Add(sum(use[i] for i in base) <= len(base) - 1)   # 같은 해 금지
        m.Maximize(sum(use[i] for i in base))               # 최대한 비슷하게
        s, st = self._solve(m, limit=10.0)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None
        return len(base) - int(s.ObjectiveValue())

    def greedy_trials(self, trials=30, seed=0):
        """
        눈대중으로 칠하는 사람 흉내.

        완전 무작위로 놓으면 어떤 문제든 성공률이 0 이라 변별이 안 된다. 사람은
        빈 칸을 아무 데나 남기지 않고 왼쪽 위부터 이어 칠하므로, 가장 앞선 빈
        칸을 덮는 배치 중 하나를 고르는 방식으로 흉내낸다.

        놓을 때마다 "이 상태로 끝까지 갈 수 있나" 를 솔버에게 묻는다. 실제로
        막히는 시점(stuck)보다 이미 글러버린 시점(doom)이 앞서는데, 그 간격이
        칠하고도 한참 뒤에야 틀린 걸 아는 구간이다.
        """
        rnd = random.Random(seed)
        by_cell = {c: [] for c in self.cells}
        for i, p in enumerate(self.places):
            for c in p:
                by_cell[c].append(i)
        order = sorted(self.cells)

        ok = 0
        dooms, blinds, blames = [], [], []

        for _ in range(trials):
            chosen, occupied = [], set()
            doomed_at = None
            while len(occupied) < len(self.cells):
                first = next(c for c in order if c not in occupied)
                cand = [i for i in by_cell[first]
                        if not (occupied & set(self.places[i]))]
                if not cand:
                    break
                i = rnd.choice(cand)
                chosen.append(i)
                occupied |= set(self.places[i])
                if doomed_at is None and not self.feasible(fixed=chosen):
                    doomed_at = len(chosen)
                    blames.append(self.blame(chosen))

            if len(occupied) == len(self.cells):
                ok += 1
                continue
            stuck = len(chosen)
            if doomed_at is None:
                doomed_at = stuck
            dooms.append(doomed_at / self.pieces)
            blinds.append((stuck - doomed_at) / self.pieces)

        avg = lambda xs: sum(xs) / len(xs) if xs else 0.0
        return {
            "success": ok / trials,
            "doom_depth": avg(dooms) if dooms else 1.0,
            "blind": avg(blinds),
            "blame": avg(blames),
        }

    def blame(self, chosen):
        """
        막힌 배치들 중 몇 개가 서로 엮여서 모순을 만드는가.

        가정으로 넣고 풀면 CP-SAT 가 최소 모순 집합을 돌려준다. 이 값이 크면
        틀린 수 하나가 아니라 여러 수가 얽혀 저 멀리서 터진다는 뜻이다.
        """
        m, use = self._model()
        lits = [use[i] for i in chosen]
        m.AddAssumptions(lits)
        s, st = self._solve(m, limit=5.0)
        if st != cp_model.INFEASIBLE:
            return 0.0
        core = s.SufficientAssumptionsForInfeasibility()
        return len(core) / len(chosen) if chosen else 0.0


# ── 점수 ────────────────────────────────────────────────────────────────

WEIGHTS = {
    "greedy_fail": 0.32,   # 이어 칠하기만으로는 못 끝내는가
    "blind":       0.22,   # 이미 글렀는데도 계속 칠하게 되는가
    "not_forced":  0.20,   # 논리만으로 안 풀리는가
    "blame":       0.12,   # 모순이 여러 수에 얽혀 있는가
    "bulk":        0.14,   # 조각 크기와 칸 수
}


def score(m):
    """0~1 성분을 가중합해 1~100 으로."""
    size_term = (m["size"] - 3) / 2                     # 3~5칸 조각
    volume_term = min(m["cells"] / 100, 1.0)
    parts = {
        "greedy_fail": 1 - m["success"],
        # 조각 절반을 헛칠하면 최대치로 본다
        "blind": min(m["blind"] * 2, 1.0),
        "not_forced": 1 - m["forced"],
        "blame": m["blame"],
        "bulk": (size_term + volume_term) / 2,
    }
    raw = sum(WEIGHTS[key] * min(max(v, 0.0), 1.0) for key, v in parts.items())
    return max(1, min(100, round(1 + 99 * raw))), parts


# ── index.html 갱신 ─────────────────────────────────────────────────────


MODE_LABEL = {"single": "한 종", "dual": "두 종"}


def emit_stages(stages):
    used = []
    for st in stages:
        for name in st["shapes"]:
            if name not in used:
                used.append(name)

    out = ["  /* ==================== 스테이지 ==================== */", ""]
    out.append("  const SHAPES = {")
    for name in used:
        out.append(f"    {name}: {SHAPE_SRC[name]},   // {SHAPE_LABEL[name]}")
    out.append("  };")
    out += [
        "",
        "  /**",
        "   * 필드는 tools/generate.py 가 CP-SAT 로 미리 풀어 구운 값이다. 각 칸이",
        "   * 정확히 한 조각에 덮이도록 제약을 걸어 만들었으므로 항상 해가 있다.",
        "   * 문자열은 좌상단부터 행 우선으로 읽는 10x10 비트맵.",
        "   *",
        "   * difficulty 는 tools/measure.py 가 잰 1~100 점수. 쉬운 순으로 정렬돼 있다.",
        "   */",
        "  const STAGES = [",
    ]
    seq = {}
    for st in stages:
        mode = st["mode"]
        seq[mode] = seq.get(mode, 0) + 1
        sol = f"{st['solutions']}{'+' if st['capped'] else ''}"
        shapes = ", ".join(f"SHAPES.{n}" for n in st["shapes"])
        label = " + ".join(SHAPE_LABEL[n] for n in st["shapes"])
        out += [
            "    {",
            f"      name: '{MODE_LABEL[mode]} {seq[mode]}',",
            f"      mode: '{mode}',",
            f"      shapes: [{shapes}],",
            f"      difficulty: {st['difficulty']},",
            f"      // {label} | {st['cells']}칸 | "
            f"해 {sol} | 강제 {st['forced'] * 100:.0f}% | "
            f"이어칠 성공률 {st['success'] * 100:.0f}% | 헛칠 {st['blind'] * 100:.0f}%",
            f"      field: '{st['field']}',",
            "    },",
        ]
    # readField 도 이 블록 안에 있다. 여기서 같이 내보내지 않으면 --apply 가
    # 블록을 통째로 갈아치울 때 정의가 사라진다.
    out += [
        "  ];",
        "",
        "  /** 비트맵 문자열 -> 칠할 수 있는 칸 집합 */",
        "  function readField(bits) {",
        "    const out = new Set();",
        "    for (let i = 0; i < bits.length; i++) {",
        "      if (bits[i] === '1') out.add(k(i % COLS, Math.floor(i / COLS)));",
        "    }",
        "    return out;",
        "  }",
        "",
    ]
    return "\n".join(out)


def apply_to_game(stages):
    html = open(GAME, encoding="utf-8").read()
    start = html.index("  /* ==================== 스테이지 ==================== */")
    end = html.index("  /* ==================== 상태 ==================== */")
    open(GAME, "w", encoding="utf-8").write(html[:start] + emit_stages(stages) + html[end:])


# ── 실행 ────────────────────────────────────────────────────────────────


def measure_one(st):
    """스테이지 하나를 재서 지표 묶음을 돌려준다. 프로세스 풀에서 돌린다."""
    names = st.get("shapes") or [st["shape"]]
    pz = Puzzle(names, st["field"])
    sols, capped = pz.count_solutions()
    forced, forced_n = pz.forced_ratio()
    swap = pz.min_swap()
    g = pz.greedy_trials()

    m = {
        "mode": st.get("mode", "single" if len(names) == 1 else "dual"),
        "shapes": names,
        "size": pz.size,
        "pieces": pz.pieces,
        "cells": len(pz.cells),
        "places": len(pz.places),
        "field": st["field"],
        "solutions": sols,
        "capped": capped,
        "forced": forced,
        "forcedPieces": forced_n,
        "minSwap": swap,
        "success": g["success"],
        "doomDepth": g["doom_depth"],
        "blind": g["blind"],
        "blame": g["blame"],
        "detTime": round(pz.det_time, 2),
    }
    m["difficulty"], m["parts"] = score(m)
    return m


def load_stages():
    """generate.py 가 뽑아 둔 필드를 모두 읽어 형식을 맞춘다."""
    out = []
    for path, mode in SOURCES:
        if not os.path.exists(path):
            continue
        for st in json.load(open(path, encoding="utf-8")):
            st.setdefault("mode", mode)
            # 예전 파일은 모양을 shape 하나로만 들고 있다
            st["shapes"] = st.get("shapes") or [st["shape"]]
            out.append(st)
    return out


def main():
    stages = load_stages()

    workers = min(os.cpu_count() or 4, 12)
    print(f"{len(stages)}개, 프로세스 {workers}개", file=sys.stderr)

    rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for m in pool.map(measure_one, stages):
            rows.append(m)
            print(f"  잼 {len(rows)}/{len(stages)}: "
                  f"{'+'.join(m['shapes'])} -> {m['difficulty']}", file=sys.stderr)

    # single 을 먼저, 각 모드 안에서 쉬운 순
    rows.sort(key=lambda r: (r["mode"] != "single", r["difficulty"], r["cells"]))

    print()
    print("모드   모양            칸  배치    해   강제  이어칠  글렀는데더칠  얽힘  교체  점수")
    for r in rows:
        sol = f"{r['solutions']}{'+' if r['capped'] else ''}"
        swap = "유일" if r["minSwap"] is None else str(r["minSwap"])
        print(
            f"{r['mode']:<7}"
            f"{'+'.join(r['shapes']):<12}"
            f"{r['cells']:>5}{r['places']:>6}"
            f"{sol:>7}"
            f"{r['forced'] * 100:>6.0f}%"
            f"{r['success'] * 100:>7.0f}%"
            f"{r['blind'] * 100:>12.0f}%"
            f"{r['blame'] * 100:>6.0f}%"
            f"{swap:>6}"
            f"{r['difficulty']:>6}"
        )

    with open(MEASURED, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if "--apply" in sys.argv:
        apply_to_game(rows)
        print("\nindex.html 갱신함", file=sys.stderr)


if __name__ == "__main__":
    main()
