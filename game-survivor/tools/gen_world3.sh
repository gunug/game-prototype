#!/bin/sh
# 월드 3 적 · 보스 전신 그림 (0.127.0) — KREA2 체인, 전신만 game-survivor/images/portrait_<id>.png
cd "$(dirname "$0")/../../game-card-world2" || exit 1
S="python tools/make_character_sheet.py --kind person --style deform --only full --out-dir ../game-survivor/images --force"
g(){ for t in 1 2 3; do $S "$@" && return 0; sleep 20; done; }
g --name splitter --label "분열 좀비" --seed 3101 --desc "a zombie lab subject with pale bluish rotting skin split down the middle by a glowing purple seam, torn white hospital gown, two-tone body as if about to divide in half"
g --name leaper   --label "도약 좀비" --seed 3102 --desc "a lean crouching zombie with long powerful mutated legs and clawed feet, grey-purple rotting skin, torn lab scrubs, poised to pounce"
g --name acider   --label "산성 좀비" --seed 3103 --desc "a hunched zombie dripping glowing green acid from its body, melting skin, a cracked chemical tank strapped to its back leaking green slime, torn hazmat suit"
g --name regener  --label "재생 좀비" --seed 3104 --desc "a muscular zombie with exposed red regenerating flesh and pulsing glowing veins, bandages and broken IV tubes hanging from its arms, torn patient gown"
g --name bossexp  --label "실험체 X" --seed 3107 --desc "a huge hulking mutant zombie experiment with grey-purple skin, an oversized clawed arm, glowing purple tumors, broken metal restraints and chains on its wrists, a barcode tattoo, torn containment suit"
g --name bossdirector --label "연구소장" --seed 3106 --desc "a tall undead zombie scientist director in a long stained white lab coat, cracked goggles with glowing green eyes, rotting grey face, one arm replaced by a mechanical laser cannon emitting red light"
echo DONE
