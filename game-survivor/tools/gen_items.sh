# 보조 아이템 그림 6장 한꺼번에 (ComfyUI 켜 둔 뒤): bash tools/gen_items.sh
cd /g/00_project/game-prototype/game-survivor
gen(){ for t in 1 2 3; do python tools/make_item.py "$@" && return 0; sleep 20; done; }
gen --id burst  --seed 3101 --prompt "a compact brass rapid-fire trigger mechanism with a small rotating drum of gears and a short ammunition belt"
gen --id count  --seed 3201 --prompt "a short steel gun muzzle attachment that splits into three flared barrels like a fork, dark gunmetal with orange heat marks"
gen --id chain  --seed 3301 --prompt "a small square electronic circuit board with glowing cyan arc lines jumping between three copper nodes"
gen --id splash --seed 3401 --prompt "a small brown leather pouch tied with string, bulging with black gunpowder, a short lit fuse on top with a spark"
gen --id reroll --seed 3501 --prompt "a single large ivory six-sided die with gold rounded edges and red pips, a faint golden shine"
gen --id banish --seed 3601 --prompt "a yellow paper talisman strip with a black ink seal symbol and a red cord tassel, slightly curled"
echo DONE
