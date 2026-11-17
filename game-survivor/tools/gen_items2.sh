# 부여 보조 4장 + 관통 강화 1장 (0.103.0, ComfyUI 켜 둔 뒤): bash tools/gen_items2.sh
cd /g/00_project/game-prototype/game-survivor
gen(){ for t in 1 2 3; do python tools/make_item.py "$@" && return 0; sleep 20; done; }
gen --id give_spread --seed 3801 --prompt "a brass wax seal stamp standing upright, its round base engraved with a fan of three diverging arrows, a blob of pink wax beside it"
gen --id give_chain  --seed 3802 --prompt "a brass wax seal stamp standing upright, its round base engraved with a zigzag lightning chain linking three dots, a blob of teal wax beside it"
gen --id give_splash --seed 3803 --prompt "a brass wax seal stamp standing upright, its round base engraved with a starburst explosion symbol, a blob of red-orange wax beside it"
gen --id give_pierce --seed 3804 --prompt "a brass wax seal stamp standing upright, its round base engraved with an arrow piercing through two circles, a blob of light blue wax beside it"
gen --id pierce      --seed 3805 --prompt "a single sharp tungsten penetrator bullet core, a long dark grey metal dart with a glowing pale blue tip"
echo DONE
