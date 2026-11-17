#!/bin/sh
# 과학자 캐릭터 (0.112.0) — 전신 portrait_scientist · 패널티 약골 · 보조 연구 일지
cd "$(dirname "$0")/../../game-card-world2" || exit 1
python tools/make_character_sheet.py --kind person --style deform --only full --out-dir ../game-survivor/images --force --name scientist --label "과학자" --seed 2201 --desc "a young scientist with messy dark hair and round glasses, a white lab coat over a light blue shirt and dark trousers, a name badge clipped to the coat, empty hands, standing ready"
cd ../game-survivor || exit 1
gen(){ for t in 1 2 3 4 5 6; do python tools/make_item.py "$@" && [ -f images/item_$2.png ] && return 0; sleep 60; done; }
gen --id pen_weak --seed 4004 --prompt "an empty orange medicine pill bottle tipped over with a cracked label and a single small pill beside it"
gen --id xp2 --seed 4005 --prompt "an open leather research notebook with glowing cyan equations and diagrams on its pages and a pen clipped to it"
echo DONE
