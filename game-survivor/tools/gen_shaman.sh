#!/bin/sh
# 주술사 캐릭터 (0.113.0) — 전신 portrait_shaman · 무기 주술인형 · 패널티 느린 걸음
cd "$(dirname "$0")/../../game-card-world2" || exit 1
for t in 1 2 3; do
  python tools/make_character_sheet.py --kind person --style deform --only full --out-dir ../game-survivor/images --force --name shaman --label "주술사" --seed 2301 --desc "a mysterious young shaman woman with long black braided hair and red face paint stripes, a dark purple hooded robe with bone beads and feather charms, a necklace of small carved talismans, empty hands, standing ready" && [ -f ../game-survivor/images/portrait_shaman.png ] && break; sleep 30; done
cd ../game-survivor || exit 1
gen(){ for t in 1 2 3 4 5 6; do python tools/make_item.py "$@" && [ -f images/item_$2.png ] && return 0; sleep 60; done; }
gen --id doll --seed 4101 --prompt "a small burlap voodoo doll with stitched button eyes, a glowing green rune on its chest and three pins stuck in it, tied with red string"
gen --id pen_slow --seed 4102 --prompt "a heavy rusty iron ball and chain shackle"
[ -f images/item_doll.png ] && mv -f images/item_doll.png images/weapon_doll.png
echo DONE
