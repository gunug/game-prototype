#!/bin/sh
# 월드 선택 그림 3장 (0.139.0) — game-card-world2/tools/make_scene.py (KREA2 · identity edit) 를 빌려 씀.
#   등장 좀비 전신 그림 둘을 기준 그림(--ref)으로 잠깐 넣고, 끝나면 지움. 결과 game-survivor/images/world_<n>.png (480×270)
#   make_scene 이 game-card-world2/docs/아이콘_목록.md 에 남기는 기록은 되돌림 (그 게임 것이 아니므로)
cd "$(dirname "$0")/../../game-card-world2" || exit 1
SV=../game-survivor/images
for n in zombie gunner spitter grenadier splitter radiant; do cp "$SV/portrait_$n.png" "images/ref/apose_sv_$n.png"; done
g(){ for t in 1 2 3; do python tools/make_scene.py --force --gen-w 1024 --gen-h 576 --out-w 480 --out-h 270 "$@" && return 0; sleep 20; done; }
g --name scene_svworld1 --ref sv_zombie,sv_gunner --seed 3301 --prompt "wide view of a ruined modern city street at dusk, abandoned cars, broken shop windows, smoke, a crowd of grey rotting zombies shambling toward the viewer, a zombie security guard in a navy uniform and cap aiming a pistol, post-apocalyptic"
g --name scene_svworld2 --ref sv_spitter,sv_grenadier --seed 3302 --prompt "wide view of a military checkpoint on the city outskirts, sandbag walls, barbed wire fences, an overturned army truck, floodlights, zombies spitting red slime and a zombie soldier throwing a grenade, post-apocalyptic"
g --name scene_svworld3 --ref sv_splitter,sv_radiant --seed 3303 --prompt "wide view of an underground research laboratory corridor, glowing green liquid tubes, shattered containment pods, flickering lights, mutant zombies in torn hospital gowns and a zombie in a yellow radiation suit with glowing cyan orbs"
for n in 1 2 3; do [ -f "images/scene/scene_svworld$n.png" ] && mv "images/scene/scene_svworld$n.png" "$SV/world_$n.png"; done
rm -f images/ref/apose_sv_*.png
git checkout -- docs/아이콘_목록.md 2>/dev/null
echo DONE
