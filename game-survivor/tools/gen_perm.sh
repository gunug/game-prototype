# 영구 업그레이드 그림 4장 (0.123.0, ComfyUI 켜 둔 뒤): bash tools/gen_perm.sh
cd /g/00_project/game-prototype/game-survivor
gen(){ for t in 1 2 3; do python tools/make_item.py "$@" && return 0; sleep 20; done; }
gen --id perm_dmg    --seed 4201 --prompt "a golden trophy medal engraved with a crossed sword and bullet, glowing purple gem in the center, royal ornate style"
gen --id perm_hp     --seed 4202 --prompt "a golden trophy medal engraved with a red heart, glowing purple gem in the center, royal ornate style"
gen --id perm_cd     --seed 4203 --prompt "a golden trophy medal engraved with a small hourglass, glowing purple gem in the center, royal ornate style"
gen --id perm_reload --seed 4204 --prompt "a golden trophy medal engraved with a bullet magazine clip, glowing purple gem in the center, royal ornate style"
echo DONE
