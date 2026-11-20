#!/bin/sh
# 건축가 (0.131.0) — 전신 portrait_builder · 무기 그림 weapon_barricade · 바리케이드 3단계 wall_wood|iron|steel
cd "$(dirname "$0")/../../game-card-world2" || exit 1
for t in 1 2 3; do
  python tools/make_character_sheet.py --kind person --style deform --only full --out-dir ../game-survivor/images --force --name builder --label "건축가" --seed 2401 --desc "a sturdy young construction worker man with a yellow hard hat, orange high-visibility vest over a grey work shirt, tool belt with hammers and wrenches, work gloves, heavy boots, empty hands, standing ready" && [ -f ../game-survivor/images/portrait_builder.png ] && break; sleep 30; done
cd ../game-survivor || exit 1
gen(){ for t in 1 2 3 4 5 6; do python tools/make_item.py "$@" && [ -f images/item_$2.png ] && return 0; sleep 60; done; }
gen --id barricade  --seed 4301 --prompt "a small portable wooden road barricade with diagonal orange and white warning stripes on folding wooden legs"
gen --id wall_wood  --seed 4302 --prompt "a square chunky wooden barricade block made of nailed rough planks, front view, sturdy and blocky"
gen --id wall_iron  --seed 4303 --prompt "a square chunky barricade block made of riveted grey iron plates bolted onto wood, front view, sturdy and blocky"
gen --id wall_steel --seed 4304 --prompt "a square chunky heavy steel barricade block with sharp metal spikes sticking out, dark steel with yellow hazard stripes, front view, sturdy and blocky"
[ -f images/item_barricade.png ] && mv -f images/item_barricade.png images/weapon_barricade.png
echo DONE
