# 고기 · 반려견 그림 (0.135.0, ComfyUI 켜 둔 뒤): bash tools/gen_meat_dog.sh
cd /g/00_project/game-prototype/game-survivor
gen(){ for t in 1 2 3; do python tools/make_item.py "$@" && return 0; sleep 20; done; }
gen --id meat --seed 4501 --prompt "a juicy roasted meat on the bone, cartoon manga meat drumstick, brown glazed, white bone handle"
gen --id dog  --seed 4502 --prompt "a loyal brown shiba inu dog with a red collar, standing side view facing right, friendly, full body"   # 결과는 왼쪽을 봄

gen --id pen_panic --seed 4504 --prompt "a pistol tumbling upside down in mid air, blue sweat drops and white motion lines around it, dropped by accident"
echo DONE
