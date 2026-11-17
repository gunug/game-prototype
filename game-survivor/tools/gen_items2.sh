# 부여 보조 인장 4장 (0.103.0 · 텅스텐 탄심은 0.104.0 에 뺌, ComfyUI 켜 둔 뒤): bash tools/gen_items2.sh
cd /g/00_project/game-prototype/game-survivor
gen(){ for t in 1 2 3; do python tools/make_item.py "$@" && return 0; sleep 20; done; }
gen --id give_spread --seed 3801 --prompt "a brass wax seal stamp standing upright, its round base engraved with a fan of three diverging arrows, a blob of pink wax beside it"
gen --id give_chain  --seed 3802 --prompt "a brass wax seal stamp standing upright, its round base engraved with a zigzag lightning chain linking three dots, a blob of teal wax beside it"
gen --id give_splash --seed 3803 --prompt "a brass wax seal stamp standing upright, its round base engraved with a starburst explosion symbol, a blob of red-orange wax beside it"
gen --id give_pierce --seed 3804 --prompt "a brass wax seal stamp standing upright, its round base engraved with an arrow piercing through two circles, a blob of light blue wax beside it"
echo DONE
gen --id magdrop --seed 3901 --prompt "a chunky red and silver horseshoe magnet with small blue-green sparkles being drawn toward its poles"
