#!/bin/sh
# 새 무기 그림 16장 (0.142.0~ , ComfyUI 켜 둔 뒤): sh tools/gen_weapons2.sh — 총구(앞)가 오른쪽
cd "$(dirname "$0")/.." || exit 1
g(){ [ -f "images/weapon_$2.png" ] && return 0; for t in 1 2 3; do python tools/make_weapon.py "$@" && return 0; sleep 20; done; }
g --id revolver --seed 1401 --prompt "a heavy six-shot revolver with a wooden grip and long steel barrel"
g --id shotgun  --seed 1402 --prompt "a pump-action shotgun with a wooden stock and wide barrel"
g --id smg      --seed 1403 --prompt "a compact black submachine gun with a long curved magazine"
g --id crossbow --seed 1404 --prompt "a tactical crossbow with a loaded bolt, limbs drawn"
g --id amr      --seed 1405 --prompt "a huge anti-materiel sniper rifle with a big muzzle brake, bipod and large scope"
g --id tesla    --seed 1406 --prompt "a handheld tesla coil gun with copper coils and blue electric sparks at the tip"
g --id chakram  --seed 1407 --prompt "a round steel chakram throwing ring with sharp outer blade, seen from the front"
g --id saw      --seed 1408 --prompt "a spinning circular saw blade with jagged teeth, seen from the front"
g --id voodoo   --seed 1409 --prompt "a small cursed voodoo skull with stitched mouth and glowing purple eyes"
g --id mine     --seed 1410 --prompt "a round military landmine with a red blinking light on top"
g --id bat      --seed 1411 --prompt "a wooden baseball bat wrapped with barbed wire and nails, handle on the left, thick end on the right"
g --id grenadeL --seed 1412 --prompt "a chunky grenade launcher with a big revolving drum cylinder"
g --id missile  --seed 1413 --prompt "a shoulder-mounted homing missile launcher tube with a red-tipped missile"
g --id drone    --seed 1414 --prompt "a small quadcopter combat drone with a little gun underneath, side view"
g --id flamer   --seed 1415 --prompt "a flamethrower with a fuel tank and a small blue pilot flame at the nozzle"
g --id poison   --seed 1416 --prompt "a glass bottle full of bubbling glowing green poison with a cork stopper"
echo DONE
# 총 모양이 아닌 것 5개는 make_weapon(손잡이 아래 · 옆모습)이 손잡이를 붙여서 make_item 으로 다시 → weapon_<id>.png 로 옮김 (0.145.0)
h(){ id=$1; shift; for t in 1 2 3; do python tools/make_item.py --id "wpn$id" "$@" && mv -f "images/item_wpn$id.png" "images/weapon_$id.png" && return 0; sleep 20; done; }
h chakram --seed 1427 --prompt "a round flat steel chakram throwing ring with a sharp bladed outer edge and a hollow center, no handle"
h saw     --seed 1428 --prompt "a single round circular saw blade with jagged steel teeth and a center hole, no handle, no tool"
h voodoo  --seed 1429 --prompt "a small cursed voodoo skull with stitched mouth, pins stuck in it and glowing purple eyes"
h mine    --seed 1430 --prompt "a round flat military landmine disc with a red blinking light on top, lying flat"
h poison  --seed 1431 --prompt "a round glass potion flask full of bubbling glowing green poison with a cork stopper"
echo DONE2
h camera  --seed 1432 --prompt "a retro instant photo camera with a big round flash bulb on top, front three-quarter view"   # 0.146.0
