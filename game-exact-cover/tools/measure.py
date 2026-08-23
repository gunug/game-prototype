"""스테이지 난이도 측정기 (OR-Tools CP-SAT).

generate.py 가 만든 필드를 읽어 난이도를 재고, 1~100 점수를 매겨 쉬운 것부터
정렬한 뒤 index.html 의 STAGES 를 다시 쓴다.

    python tools/measure.py            # 재기만 하고 표로 보여줌
    python tools/measure.py --apply    # index.html 의 STAGES 까지 갱신

솔버가 그냥 뱉는 num_conflicts / num_branches 는 쓰지 않는다. CP-SAT 전처리가
정확한 덮개에 워낙 강해서 사람이 헤매는 문제도 충돌 0 으로 끝나 변별력이 없다.
대신 "사람이 저지를 법한 상황"을 만들어 놓고 솔버에게 물어보는 값을 쓴다.
"""

import hashlib
import json
import os
import random
import re
import sys
from concurrent.futures import ProcessPoolExecutor

from ortools.sat.python import cp_model

from generate import COLS, ROWS, SHAPES, placements, rotations, idx

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
        # 회전해도 같은 칸을 덮는 형태는 하나로 친다. 정사각형은 1, 막대와 번개는 2
        self.rots = [len(rotations(sh)) for sh in self.shapes]
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

    def branching(self):
        """
        칸 하나를 놓고 볼 때 후보가 몇 개나 되는가. 같은 넓이라도 모양이 둘이면
        회전까지 곱해져 후보가 확 늘어난다. 솔버 없이 세는 값이다.
        """
        n = 0
        for p in self.places:
            n += len(p)
        return n / len(self.cells)

    def deduction(self, limit_steps=40):
        """
        가장 앞선 빈 칸부터 채워 나가며 두 가지를 잰다.

        - 확인 비용: 그 칸을 덮을 수 있는 후보가 몇 개인가. 후보가 하나뿐이면
          눈에 바로 보이는 강제 수고, 여럿이면 하나씩 따져 봐야 한다.
        - 추측 비율: 후보를 다 따져도 둘 이상 살아남는 자리의 비율.

        강제 비율은 솔버가 증명한 전역 성질이라 "사람이 알아볼 수 있는가" 를
        담지 못한다. 같은 강제 100% 라도 후보 1개짜리와 8개짜리는 전혀 다르다.
        """
        by_cell = {c: [] for c in self.cells}
        for i, p in enumerate(self.places):
            for c in p:
                by_cell[c].append(i)
        order = sorted(self.cells)

        chosen, occupied = [], set()
        checks, guesses, steps = [], 0, 0

        while len(occupied) < len(self.cells) and steps < limit_steps:
            first = next((c for c in order if c not in occupied), None)
            if first is None:
                break
            cand = [i for i in by_cell[first] if not (occupied & set(self.places[i]))]
            if not cand:
                break
            checks.append(len(cand))
            viable = [i for i in cand if self.feasible(fixed=chosen + [i])]
            if not viable:
                break
            steps += 1
            if len(viable) > 1:
                guesses += 1
            chosen.append(viable[0])
            occupied |= set(self.places[viable[0]])

        return {
            "check": sum(checks) / len(checks) if checks else 1.0,
            "guess": guesses / steps if steps else 0.0,
        }

    # ── 반박 깊이 ──

    def _frontier(self, occupied):
        """읽는 순서로 가장 앞선 빈 칸과, 그 칸을 덮을 수 있는 배치들."""
        for c in self._order:
            if c not in occupied:
                return c, [i for i in self._by_cell[c] if not (occupied & self._sets[i])]
        return None, []

    def _refutable(self, occupied, k):
        """
        k 수 안에 막힌다는 걸 보일 수 있는가.

        가장 앞선 빈 칸은 반드시 덮어야 하므로 거기서만 갈라도 반박은 완전하다.
        덮을 방법이 아예 없으면 그 자리에서 모순이고, 아니면 모든 갈래가
        한 수 얕은 깊이에서 막혀야 반박이 선다.
        """
        first, cand = self._frontier(occupied)
        if first is None:
            return False            # 다 채웠으면 모순이 아니다
        if not cand:
            return True             # 못 덮는 칸이 생겼다
        if k <= 1:
            return False            # 더 볼 수 없다
        return all(self._refutable(occupied | self._sets[i], k - 1) for i in cand)

    def _depth_of(self, occupied, p, cap):
        """틀린 배치 p 를 쳐내는 데 필요한 수. cap 안에 안 되면 cap + 1."""
        after = occupied | self._sets[p]
        for k in range(1, cap + 1):
            if self._refutable(after, k):
                return k
        return cap + 1

    def refute_depth(self, cap=8, limit_steps=40):
        """
        풀어 나가면서 자리마다 "틀린 후보를 쳐내는 데 몇 수가 필요한가" 를 잰다.

        후보가 하나뿐인 자리는 0수. 고를 게 없으니 생각도 없다.
        후보가 여럿이면 틀린 것을 전부 쳐내야 하므로 그중 가장 깊은 것이 그 자리의 깊이다.
        """
        self._sets = [set(p) for p in self.places]
        self._by_cell = {c: [] for c in self.cells}
        for i, p in enumerate(self.places):
            for c in p:
                self._by_cell[c].append(i)
        self._order = sorted(self.cells)

        chosen, occupied = [], set()
        per_step = []

        while len(occupied) < len(self.cells) and len(per_step) < limit_steps:
            first, cand = self._frontier(occupied)
            if first is None or not cand:
                break

            if len(cand) == 1:
                per_step.append(0)
                chosen.append(cand[0])
                occupied |= self._sets[cand[0]]
                continue

            viable = [i for i in cand if self.feasible(fixed=chosen + [i])]
            if not viable:
                break
            wrong = [i for i in cand if i not in viable]
            per_step.append(max((self._depth_of(occupied, w, cap) for w in wrong), default=0))
            chosen.append(viable[0])
            occupied |= self._sets[viable[0]]

        return {
            "depth": max(per_step) if per_step else 0,
            "depthCap": cap,
            "steps": per_step,
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
    "branch":      0.20,   # 같은 넓이에 놓을 수 있는 방법이 얼마나 많은가
    "check":       0.15,   # 한 자리를 정하려고 후보를 몇 개나 따져야 하는가
    "greedy_fail": 0.22,   # 이어 칠하기만으로는 못 끝내는가
    "blind":       0.18,   # 이미 글렀는데도 계속 칠하게 되는가
    "guess":       0.10,   # 따져 봐도 답이 하나로 안 좁혀지는 자리의 비율
    "blame":       0.08,   # 모순이 여러 수에 얽혀 있는가
    "bulk":        0.07,   # 조각 크기와 칸 수
}


BANDS = ("그냥", "추론", "탐색", "중간")


def band(m):
    """
    퍼즐이 어떤 식으로 풀리는지 한 마디로.

    - 그냥: 후보가 늘 하나뿐이라 따질 것 없이 채워진다
    - 추론: 후보가 여럿인데 따져 보면 하나로 좁혀진다 (수도쿠에서 재미있는 자리)
    - 탐색: 따져도 안 좁혀져 시행착오가 필요하다
    - 중간: 그 사이
    """
    if m["guess"] >= 0.20:
        return "탐색"
    if m["check"] >= 2.0 and m["guess"] == 0:
        return "추론"
    if m["check"] < 1.5:
        return "그냥"
    return "중간"


def score(m):
    """0~1 성분을 가중합해 1~100 으로."""
    size_term = (m["size"] - 3) / 2                     # 3~5칸 조각
    volume_term = min(m["cells"] / 100, 1.0)
    parts = {
        # 한 종은 칸당 후보가 5 안팎, 두 종은 15 를 넘는다. 16 을 위쪽 끝으로 본다
        "branch": min(m["branch"] / 16, 1.0),
        # 후보가 하나면 공짜, 아홉이면 최대치
        "check": min((m["check"] - 1) / 8, 1.0),
        "greedy_fail": 1 - m["success"],
        # 조각 절반을 헛칠하면 최대치로 본다
        "blind": min(m["blind"] * 2, 1.0),
        "guess": m["guess"],
        "blame": m["blame"],
        "bulk": (size_term + volume_term) / 2,
    }
    raw = sum(WEIGHTS[key] * min(max(v, 0.0), 1.0) for key, v in parts.items())
    return max(1, min(100, round(1 + 99 * raw))), parts


# ── index.html 갱신 ─────────────────────────────────────────────────────


MODE_LABEL = {"single": "한 종", "dual": "두 종"}


def stage_id(st):
    """
    스테이지를 가리키는 안정된 키.

    번호는 정렬이 바뀔 때마다 옮겨 다녀서 클리어 기록이 엉뚱한 퍼즐에 붙는다.
    내용으로 매기면 다시 재고 다시 정렬해도 그대로다.
    """
    raw = "+".join(st["shapes"]) + "|" + st["field"]
    return "+".join(st["shapes"]) + "-" + hashlib.sha1(raw.encode()).hexdigest()[:8]


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
    for st in stages:
        mode = st["mode"]
        sol = f"{st['solutions']}{'+' if st['capped'] else ''}"
        shapes = ", ".join(f"SHAPES.{n}" for n in st["shapes"])
        label = " + ".join(SHAPE_LABEL[n] for n in st["shapes"])
        out += [
            "    {",
            f"      id: '{stage_id(st)}',",
            f"      mode: '{mode}',",
            f"      shapes: [{shapes}],",
            f"      depth: {st['depth']},",
            f"      depthCap: {st['depthCap']},",
            f"      difficulty: {st['difficulty']},",
            f"      // {label} | {st['cells']}칸 | "
            f"반박 깊이 {st['depth']}{'+' if st['depth'] > st['depthCap'] else ''}수 | "
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
    d = pz.deduction()
    rd = pz.refute_depth()

    m = {
        "mode": st.get("mode", "single" if len(names) == 1 else "dual"),
        "shapes": names,
        "size": pz.size,
        "rots": pz.rots,
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
        "branch": pz.branching(),
        "check": d["check"],
        "guess": d["guess"],
        "depth": rd["depth"],
        "depthCap": rd["depthCap"],
        "depthSteps": rd["steps"],
        "detTime": round(pz.det_time, 2),
    }
    m["difficulty"], m["parts"] = score(m)
    m["band"] = band(m)
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
    # 반박 깊이가 1차, 난이도 점수가 2차
    rows.sort(key=lambda r: (r["mode"] != "single", r["depth"], r["difficulty"], r["cells"]))

    print()
    print("모드   모양        회전  칸  배치  칸당후보 확인비용 추측  해     강제  이어칠 헛칠  점수  깊이")
    for r in rows:
        sol = f"{r['solutions']}{'+' if r['capped'] else ''}"
        swap = "유일" if r["minSwap"] is None else str(r["minSwap"])
        print(
            f"{r['mode']:<7}"
            f"{'+'.join(r['shapes']):<12}"
            f"{'+'.join(str(n) for n in r['rots']):>4}"
            f"{r['cells']:>5}{r['places']:>6}"
            f"{r['branch']:>9.1f}"
            f"{r['check']:>9.1f}"
            f"{r['guess'] * 100:>5.0f}%"
            f"{sol:>7}"
            f"{r['forced'] * 100:>6.0f}%"
            f"{r['success'] * 100:>6.0f}%"
            f"{r['blind'] * 100:>5.0f}%"
            f"{r['difficulty']:>6}"
            f"{r['depth']:>5}수"
        )

    with open(MEASURED, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if "--apply" in sys.argv:
        apply_to_game(rows)
        print("\nindex.html 갱신함", file=sys.stderr)


if __name__ == "__main__":
    main()
