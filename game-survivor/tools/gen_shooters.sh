#!/bin/sh
# 월드 1 · 3 탄 쏘는 좀비 전신 그림 (0.139.0) — KREA2 체인, 전신만 game-survivor/images/portrait_<id>.png
cd "$(dirname "$0")/../../game-card-world2" || exit 1
S="python tools/make_character_sheet.py --kind person --style deform --only full --out-dir ../game-survivor/images --force"
g(){ for t in 1 2 3; do $S "$@" && return 0; sleep 20; done; }
g --name gunner  --label "총잡이 좀비" --seed 3201 --desc "a zombie security guard in a torn navy uniform and cap, grey rotting skin, holding a pistol aimed forward with one arm, city street survivor look"
g --name radiant --label "방사 좀비"   --seed 3202 --desc "a zombie lab worker in a torn yellow radiation suit, cracked visor, glowing cyan orbs of energy swirling around its raised hands, grey rotting skin"
echo DONE
