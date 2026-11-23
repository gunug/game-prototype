# 소방관 보조 '소화기 분사' 그림 (0.136.0, ComfyUI 켜 둔 뒤): bash tools/gen_ffsub.sh
cd /g/00_project/game-prototype/game-survivor
gen(){ for t in 1 2 3; do python tools/make_item.py "$@" && return 0; sleep 20; done; }
gen --id foam --seed 4601 --prompt "a red fire extinguisher spraying a big burst of white foam cloud from its nozzle"
echo DONE
