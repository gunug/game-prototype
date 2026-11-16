#!/bin/sh
# 월드 2 적 · 보스 전신 그림 (0.84.0) — KREA2 체인, 전신만 game-survivor/images/portrait_<id>.png
cd "$(dirname "$0")/../../game-card-world2" || exit 1
S="python tools/make_character_sheet.py --kind person --style deform --only full --out-dir ../game-survivor/images --force"
$S --name spitter  --label "침 좀비" --seed 2101 --desc "a gaunt zombie with grey-green rotting skin, a grotesquely swollen glowing green throat and acid drool dripping from its open jaw, torn grey hoodie, hunched forward"
$S --name grenadier --label "수류탄 좀비" --seed 2102 --desc "a zombie soldier with pale rotting skin in torn olive military fatigues and a dented helmet, a bandolier of grenades across the chest, one hand raised holding a grenade"
$S --name shielder --label "방패 좀비" --seed 2103 --desc "a hulking zombie with grey rotting skin in a torn mechanic jumpsuit, holding a large dented red car door in front of its body like a shield"
$S --name bloater  --label "부푼 좀비" --seed 2104 --desc "a hugely bloated round zombie with sickly yellow-green swollen skin covered in glowing pustules, tiny legs, torn stretched t-shirt, about to burst"
$S --name bossmortar --label "포격 하사" --seed 2107 --desc "a huge muscular undead zombie sergeant with grey-green rotting skin, sunken glowing yellow eyes, exposed teeth and stitched wounds, in torn camouflage with a heavy armored vest, a grenade launcher held in both hands, rows of shells on belts, a cracked gas mask hanging at the neck"
$S --name bossgeneral --label "기지의 장군" --seed 2106 --desc "a towering zombie general in a long torn dark green military greatcoat with gold epaulettes and rows of medals, a peaked officer cap, rotting grey face with glowing red eyes, a cavalry saber in one hand"
