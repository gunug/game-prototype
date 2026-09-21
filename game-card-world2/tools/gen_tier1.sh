#!/bin/sh
# 1티어 새 카드 아이콘 8장 (2026-09-17). 기존 그림 재사용: stone, flint, tree, berry
cd "$(dirname "$0")/.."
O="an inanimate object only, no face, no eyes, no arms, no legs, no people, no creatures:"
run(){ python -u tools/make_icon_object.py --force "$@" || echo "FAIL $2"; }
run --name card_ore --label "광석" --bg white --prompt "$O a chunk of raw ore rock, rough grey stone with bright copper orange and rusty iron veins and glittering metallic flecks, freshly broken jagged faces"
run --name card_sap --label "수액" --prompt "$O a thick glossy blob of golden amber tree sap, translucent honey colored resin with a bright highlight and a small drip running down"
run --name card_water --label "물" --prompt "$O a single big clear blue water droplet above a small splash puddle, glossy transparent water with bright highlights and ripples"
run --name card_soil --label "흙" --bg white --prompt "$O a small heap of rich dark brown soil, loose crumbly earth clumps with tiny pebbles and a few thin root threads"
run --name card_sand --label "모래" --prompt "$O a small conical heap of golden beige sand, fine grainy texture with tiny sparkles"
run --name card_grass --label "풀" --prompt "$O a lush tuft of fresh green wild grass, long blades bending gracefully, vivid green with lighter tips, no flowers"
python -u tools/make_icon_character.py --force --name card_beast --label "짐승" --bg white --prompt "full body of a wild boar beast standing, stocky body, bristly dark brown fur, small curved tusks, fierce small eyes, side three-quarter view"
run --name card_seed --label "씨앗" --bg white --prompt "$O a small cluster of three plump wild grain seeds, brown and golden husks with fine stripes, one seed split open showing the pale inside"
echo DONE
