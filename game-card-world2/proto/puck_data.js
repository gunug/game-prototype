// tools/puck_data.mjs 가 index.html 에서 뽑음 — 손으로 고치지 않는다
const PUCK_DATA = {
 "saveKey": "card-world2.v1",
 "baseRange": 1,
 "baseAps": 1,
 "heroes": {
  "knight": {
   "name": "가렛",
   "job": "기사",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 18,
    "spd": 3
   },
   "aps": 1,
   "arm": "melee",
   "trait": "gate",
   "tip": "문 앞 — 맨 앞에 서면 방어 +2",
   "slots": [
    "weapon",
    "armor",
    "shield",
    "trinket",
    "consumable"
   ],
   "pic": "bust_knight",
   "card": "card_knight"
  },
  "ally": {
   "name": "세리나",
   "job": "궁수",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 14,
    "spd": 4
   },
   "aps": 1,
   "arm": "bow",
   "trait": "rapid",
   "tip": "연사 — 10초에 2타 더",
   "slots": [
    "weapon",
    "armor",
    "shield",
    "trinket",
    "consumable"
   ],
   "pic": "bust_archer",
   "card": "card_archer"
  },
  "shieldsmith": {
   "name": "토른",
   "job": "방패 장인",
   "body": {
    "atk": 1,
    "def": 1,
    "hp": 24,
    "spd": 2
   },
   "aps": 0.8,
   "arm": null,
   "trait": "shell",
   "tip": "껍질 — 방패 칸 셋 · 무기 없음",
   "slots": [
    "armor",
    "shield",
    "shield2",
    "shield3",
    "consumable"
   ],
   "pic": "bust_shieldsmith",
   "card": "card_shieldsmith"
  },
  "weaponsmith": {
   "name": "두르간",
   "job": "무기 장인",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 16,
    "spd": 3
   },
   "aps": 0.8,
   "arm": "axe",
   "trait": "dual",
   "tip": "양손 — 무기 칸 둘 (둘째 무기는 공격만 더한다)",
   "slots": [
    "weapon",
    "weapon2",
    "armor",
    "shield",
    "trinket"
   ],
   "pic": "bust_weaponsmith",
   "card": "card_weaponsmith"
  },
  "armorsmith": {
   "name": "마르그",
   "job": "갑옷 장인",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 16,
    "spd": 2
   },
   "aps": 0.8,
   "arm": "axe",
   "trait": "lining",
   "tip": "안감 — 갑옷을 입으면 방어 +2",
   "slots": [
    "weapon",
    "armor",
    "shield",
    "trinket",
    "consumable"
   ],
   "pic": "bust_armorsmith",
   "card": "card_armorsmith"
  },
  "keeper": {
   "name": "보른",
   "job": "여관 주인",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 24,
    "spd": 2
   },
   "aps": 0.8,
   "arm": "spear",
   "trait": "big",
   "tip": "덩치 — 몸이 크다 (체력 24)",
   "slots": [
    "weapon",
    "armor",
    "shield",
    "trinket",
    "consumable"
   ],
   "pic": "bust_innkeeper",
   "card": "card_innkeeper"
  },
  "carpenter": {
   "name": "헤이든",
   "job": "목수",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 15,
    "spd": 3
   },
   "aps": 0.8,
   "arm": "spear",
   "trait": "reach",
   "tip": "긴 자루 — 창 사거리 +1",
   "slots": [
    "weapon",
    "armor",
    "shield",
    "trinket",
    "consumable"
   ],
   "pic": "bust_carpenter",
   "card": "card_carpenter"
  },
  "cook": {
   "name": "올가",
   "job": "요리사",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 16,
    "spd": 3
   },
   "aps": 0.8,
   "arm": "spear",
   "trait": "pantry",
   "tip": "곳간 — 소모품 칸 셋",
   "slots": [
    "weapon",
    "trinket",
    "consumable",
    "consumable2",
    "consumable3"
   ],
   "pic": "bust_cook",
   "card": "card_cook"
  },
  "peddler": {
   "name": "오르반",
   "job": "만물상",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 12,
    "spd": 3
   },
   "aps": 0.8,
   "arm": "bow",
   "trait": "know",
   "tip": "아는 것 — 적 방어를 2 덜 받는다",
   "slots": [
    "weapon",
    "armor",
    "shield",
    "trinket",
    "consumable"
   ],
   "pic": "bust_peddler",
   "card": "card_peddler"
  },
  "trinketsmith": {
   "name": "네이라",
   "job": "장신구 장인",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 12,
    "spd": 4
   },
   "aps": 0.8,
   "arm": "bow",
   "trait": "hoard",
   "tip": "모으기 — 장신구 칸 넷",
   "slots": [
    "weapon",
    "trinket",
    "trinket2",
    "trinket3",
    "trinket4"
   ],
   "pic": "bust_trinketsmith",
   "card": "card_trinketsmith"
  },
  "herbalist": {
   "name": "실바",
   "job": "약재 장인",
   "body": {
    "atk": 1,
    "def": 0,
    "hp": 12,
    "spd": 3
   },
   "aps": 0.8,
   "arm": "bow",
   "trait": "mend",
   "tip": "약손 — 소모품 칸 셋 · 함께 나간 일행이 싸우는 동안 10초에 3 더 아문다",
   "slots": [
    "weapon",
    "armor",
    "consumable",
    "consumable2",
    "consumable3"
   ],
   "pic": "bust_herbalist",
   "card": "card_herbalist"
  }
 },
 "gear": {
  "stoneknife": {
   "name": "뗀석기 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 3,
   "atk": 1,
   "rate": 12,
   "aps": 1.2
  },
  "handaxe": {
   "name": "손도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 4,
   "atk": 4,
   "rate": 9,
   "aps": 0.9
  },
  "leatherarmor": {
   "name": "가죽 갑옷",
   "tags": [
    "armor"
   ],
   "step": 3,
   "def": 1
  },
  "woodshield": {
   "name": "나무 방패",
   "tags": [
    "shield"
   ],
   "step": 3,
   "def": 1
  },
  "rimshield": {
   "name": "테 방패",
   "tags": [
    "shield"
   ],
   "step": 4,
   "def": 2
  },
  "battleaxe": {
   "name": "전투 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 5,
   "atk": 6,
   "rate": 8,
   "aps": 0.8,
   "pierce": true
  },
  "obsidianknife": {
   "name": "흑요석 칼",
   "tags": [
    "melee"
   ],
   "step": 5,
   "atk": 5,
   "rate": 9,
   "aps": 0.9,
   "bleed": 2
  },
  "woodbow": {
   "name": "나무 활",
   "tags": [
    "bow"
   ],
   "step": 3,
   "atk": 1,
   "range": 5,
   "rate": 11,
   "aps": 1.1
  },
  "huntbow": {
   "name": "사냥 활",
   "tags": [
    "bow"
   ],
   "step": 4,
   "atk": 4,
   "range": 5,
   "rate": 8,
   "aps": 0.8
  },
  "obsidianbow": {
   "name": "흑요 활",
   "tags": [
    "bow"
   ],
   "step": 5,
   "atk": 5,
   "range": 5,
   "rate": 10,
   "aps": 1,
   "bleed": 1
  },
  "ironaxe": {
   "name": "쇠 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 6,
   "atk": 8,
   "rate": 8,
   "aps": 0.8,
   "pierce": true
  },
  "tuskaxe": {
   "name": "엄니 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 7,
   "atk": 10,
   "rate": 8,
   "aps": 0.8,
   "pierce": true
  },
  "chainaxe": {
   "name": "사슬 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 8,
   "atk": 13,
   "rate": 8,
   "aps": 0.8,
   "pierce": true
  },
  "shardaxe": {
   "name": "파편 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 9,
   "atk": 16,
   "rate": 8,
   "aps": 0.8,
   "pierce": true
  },
  "webbow": {
   "name": "거미줄 활",
   "tags": [
    "bow"
   ],
   "step": 5,
   "atk": 4,
   "range": 5,
   "rate": 10,
   "aps": 1,
   "multi": 2
  },
  "shellbow": {
   "name": "갑각 활",
   "tags": [
    "bow"
   ],
   "step": 7,
   "atk": 8,
   "range": 6,
   "rate": 11,
   "aps": 1.1,
   "bleed": 3
  },
  "hoopbow": {
   "name": "쇠테 활",
   "tags": [
    "bow"
   ],
   "step": 8,
   "atk": 9,
   "range": 7,
   "rate": 12,
   "aps": 1.2,
   "bleed": 4
  },
  "shardbow": {
   "name": "파편 활",
   "tags": [
    "bow"
   ],
   "step": 9,
   "atk": 11,
   "range": 8,
   "rate": 11,
   "aps": 1.1,
   "bleed": 5
  },
  "fangspear": {
   "name": "송곳니 창",
   "tags": [
    "melee",
    "spear"
   ],
   "step": 3,
   "atk": 1,
   "range": 2,
   "rate": 11,
   "aps": 1.1
  },
  "obsspear": {
   "name": "흑요석 창",
   "tags": [
    "melee",
    "spear"
   ],
   "step": 4,
   "atk": 4,
   "range": 3,
   "rate": 8,
   "aps": 0.8
  },
  "ironspear": {
   "name": "쇠 창",
   "tags": [
    "melee",
    "spear"
   ],
   "step": 5,
   "atk": 7,
   "range": 3,
   "rate": 8,
   "aps": 0.8
  },
  "tuskspear": {
   "name": "엄니 창",
   "tags": [
    "melee",
    "spear"
   ],
   "step": 6,
   "atk": 9,
   "range": 3,
   "rate": 10,
   "aps": 1
  },
  "chainspear": {
   "name": "사슬 창",
   "tags": [
    "melee",
    "spear"
   ],
   "step": 7,
   "atk": 12,
   "range": 3,
   "rate": 9,
   "aps": 0.9
  },
  "shardspear": {
   "name": "파편 창",
   "tags": [
    "melee",
    "spear"
   ],
   "step": 8,
   "atk": 15,
   "range": 3,
   "rate": 9,
   "aps": 0.9
  },
  "twinaxe": {
   "name": "쌍날 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 5,
   "atk": 4,
   "rate": 12,
   "aps": 1.2,
   "multi": 2
  },
  "pincaxe": {
   "name": "집게 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 6,
   "atk": 5,
   "rate": 11,
   "aps": 1.1,
   "multi": 3
  },
  "sawaxe": {
   "name": "톱니 도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 7,
   "atk": 6,
   "rate": 10,
   "aps": 1,
   "multi": 4
  },
  "chaintwin": {
   "name": "사슬 쌍도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 8,
   "atk": 7,
   "rate": 10,
   "aps": 1,
   "multi": 5
  },
  "shardtwin": {
   "name": "파편 쌍도끼",
   "tags": [
    "melee",
    "axe"
   ],
   "step": 9,
   "atk": 8,
   "rate": 10,
   "aps": 1,
   "multi": 6
  },
  "toothdagger": {
   "name": "이빨 단검",
   "tags": [
    "melee"
   ],
   "step": 3,
   "atk": 1,
   "rate": 12,
   "aps": 1.2
  },
  "boneknife": {
   "name": "뼈 칼",
   "tags": [
    "melee"
   ],
   "step": 4,
   "atk": 4,
   "rate": 9,
   "aps": 0.9
  },
  "venomknife": {
   "name": "독니 칼",
   "tags": [
    "melee"
   ],
   "step": 6,
   "atk": 6,
   "rate": 11,
   "aps": 1.1,
   "bleed": 3
  },
  "shellknife": {
   "name": "갑각 칼",
   "tags": [
    "melee"
   ],
   "step": 7,
   "atk": 8,
   "rate": 10,
   "aps": 1,
   "bleed": 4
  },
  "silkknife": {
   "name": "비단 칼",
   "tags": [
    "melee"
   ],
   "step": 8,
   "atk": 9,
   "rate": 11,
   "aps": 1.1,
   "bleed": 5
  },
  "shardknife": {
   "name": "파편 칼",
   "tags": [
    "melee"
   ],
   "step": 9,
   "atk": 11,
   "rate": 11,
   "aps": 1.1,
   "bleed": 6
  },
  "venombow": {
   "name": "독 활",
   "tags": [
    "bow"
   ],
   "step": 6,
   "atk": 6,
   "range": 6,
   "rate": 12,
   "aps": 1.2,
   "bleed": 2
  },
  "layerbow": {
   "name": "겹살 활",
   "tags": [
    "bow"
   ],
   "step": 6,
   "atk": 5,
   "range": 6,
   "rate": 10,
   "aps": 1,
   "multi": 3
  },
  "clambow": {
   "name": "조개 활",
   "tags": [
    "bow"
   ],
   "step": 7,
   "atk": 6,
   "range": 6,
   "rate": 9,
   "aps": 0.9,
   "multi": 4
  },
  "chainbow": {
   "name": "사슬 활",
   "tags": [
    "bow"
   ],
   "step": 8,
   "atk": 7,
   "range": 7,
   "rate": 9,
   "aps": 0.9,
   "multi": 5
  },
  "shardrapid": {
   "name": "파편 연사활",
   "tags": [
    "bow"
   ],
   "step": 9,
   "atk": 8,
   "range": 8,
   "rate": 9,
   "aps": 0.9,
   "multi": 6
  },
  "stonearmor": {
   "name": "돌가죽 갑옷",
   "tags": [
    "armor"
   ],
   "step": 4,
   "def": 3
  },
  "spikemail": {
   "name": "가시 갑옷",
   "tags": [
    "armor"
   ],
   "step": 5,
   "def": 4,
   "thorns": 1
  },
  "ironmail": {
   "name": "쇠누빔 갑옷",
   "tags": [
    "armor"
   ],
   "step": 6,
   "def": 6,
   "thorns": 2
  },
  "chitinmail": {
   "name": "지네 갑옷",
   "tags": [
    "armor"
   ],
   "step": 7,
   "def": 8,
   "thorns": 3
  },
  "chainmail": {
   "name": "쇠미늘 갑옷",
   "tags": [
    "armor"
   ],
   "step": 8,
   "def": 10,
   "thorns": 4
  },
  "shardarmor": {
   "name": "파편 갑옷",
   "tags": [
    "armor"
   ],
   "step": 9,
   "def": 12,
   "thorns": 5
  },
  "toadmail": {
   "name": "두꺼비 갑옷",
   "tags": [
    "armor"
   ],
   "step": 5,
   "def": 4,
   "burnguard": 2
  },
  "shellarmor": {
   "name": "갑각 갑옷",
   "tags": [
    "armor"
   ],
   "step": 6,
   "def": 6,
   "burnguard": 3
  },
  "charmail": {
   "name": "그을린 갑옷",
   "tags": [
    "armor"
   ],
   "step": 7,
   "def": 8,
   "burnguard": 4
  },
  "hoopmail": {
   "name": "쇠테 갑옷",
   "tags": [
    "armor"
   ],
   "step": 8,
   "def": 10,
   "burnguard": 5
  },
  "shardfire": {
   "name": "파편 화갑",
   "tags": [
    "armor"
   ],
   "step": 9,
   "def": 12,
   "burnguard": 6
  },
  "scaleshield": {
   "name": "돌비늘 방패",
   "tags": [
    "shield"
   ],
   "step": 5,
   "def": 3,
   "shell": 1
  },
  "nacreshield": {
   "name": "자개 방패",
   "tags": [
    "shield"
   ],
   "step": 6,
   "def": 4,
   "shell": 2
  },
  "chitinshield": {
   "name": "지네 방패",
   "tags": [
    "shield"
   ],
   "step": 7,
   "def": 5,
   "shell": 3
  },
  "hoopshield": {
   "name": "쇠테 방패",
   "tags": [
    "shield"
   ],
   "step": 8,
   "def": 6,
   "shell": 4
  },
  "shardshield": {
   "name": "파편 방패",
   "tags": [
    "shield"
   ],
   "step": 9,
   "def": 7,
   "shell": 5
  },
  "stoneshield": {
   "name": "돌가죽 방패",
   "tags": [
    "shield"
   ],
   "step": 5,
   "def": 5
  },
  "slabshield": {
   "name": "석판 방패",
   "tags": [
    "shield"
   ],
   "step": 6,
   "def": 7
  },
  "tuskshield": {
   "name": "엄니 방패",
   "tags": [
    "shield"
   ],
   "step": 7,
   "def": 9
  },
  "chainshield": {
   "name": "사슬 방패",
   "tags": [
    "shield"
   ],
   "step": 8,
   "def": 11
  },
  "shardwall": {
   "name": "파편 큰방패",
   "tags": [
    "shield"
   ],
   "step": 9,
   "def": 13
  }
 },
 "foes": {
  "animal": {
   "name": "토끼",
   "atk": 1,
   "def": 0,
   "hp": 3,
   "spd": 4,
   "aps": 1.2,
   "portrait": "portrait_animal"
  },
  "wolf": {
   "name": "늑대",
   "atk": 2,
   "def": 0,
   "hp": 6,
   "spd": 4,
   "portrait": "portrait_wolf"
  },
  "bear": {
   "name": "곰",
   "atk": 3,
   "def": 0,
   "hp": 9,
   "spd": 3,
   "aps": 0.8,
   "portrait": "portrait_bear"
  },
  "wilddog": {
   "name": "들개",
   "atk": 2,
   "def": 0,
   "hp": 6,
   "spd": 4,
   "aps": 1.2,
   "portrait": "portrait_wilddog"
  },
  "boar": {
   "name": "멧돼지",
   "atk": 3,
   "def": 0,
   "hp": 10,
   "spd": 5,
   "aps": 0.8,
   "portrait": "portrait_boar"
  },
  "bison": {
   "name": "들소",
   "atk": 4,
   "def": 1,
   "hp": 14,
   "spd": 4,
   "aps": 0.8,
   "portrait": "portrait_bison"
  },
  "fox": {
   "name": "여우",
   "atk": 3,
   "def": 0,
   "hp": 16,
   "spd": 5,
   "aps": 1.2,
   "portrait": "portrait_fox"
  },
  "wolfleader": {
   "name": "늑대 두목",
   "atk": 4,
   "def": 1,
   "hp": 18,
   "spd": 4,
   "aps": 0.9,
   "portrait": "portrait_wolfleader"
  },
  "forestbear": {
   "name": "숲곰",
   "atk": 5,
   "def": 1,
   "hp": 26,
   "spd": 3,
   "aps": 0.8,
   "portrait": "portrait_forestbear"
  },
  "stonebug": {
   "name": "돌벌레",
   "atk": 4,
   "def": 4,
   "hp": 6,
   "spd": 2,
   "portrait": "portrait_stonebug"
  },
  "shellback": {
   "name": "바위 등껍질",
   "atk": 5,
   "def": 8,
   "hp": 10,
   "spd": 1,
   "aps": 0.8,
   "portrait": "portrait_shellback"
  },
  "stonelord": {
   "name": "돌가죽 주인",
   "atk": 6,
   "def": 10,
   "hp": 20,
   "spd": 2,
   "aps": 0.9,
   "portrait": "portrait_stonelord"
  },
  "mosstoad": {
   "name": "이끼 두꺼비",
   "atk": 6,
   "def": 2,
   "hp": 12,
   "spd": 2,
   "regen": 1,
   "portrait": "portrait_mosstoad"
  },
  "bogarm": {
   "name": "수렁 팔",
   "atk": 9,
   "def": 4,
   "hp": 20,
   "spd": 1,
   "aps": 0.9,
   "range": 2,
   "regen": 3,
   "portrait": "portrait_bogarm"
  },
  "tombkeeper": {
   "name": "무덤 주인",
   "atk": 10,
   "def": 3,
   "hp": 30,
   "spd": 2,
   "aps": 0.9,
   "regen": 10,
   "portrait": "portrait_tombkeeper"
  },
  "crayfish": {
   "name": "가재",
   "atk": 5,
   "def": 0,
   "hp": 16,
   "spd": 2,
   "portrait": "portrait_crayfish"
  },
  "crocodile": {
   "name": "악어",
   "atk": 7,
   "def": 3,
   "hp": 44,
   "spd": 3,
   "aps": 0.9,
   "portrait": "portrait_crocodile"
  },
  "catfish": {
   "name": "큰 메기",
   "atk": 9,
   "def": 3,
   "hp": 60,
   "spd": 3,
   "aps": 0.9,
   "portrait": "portrait_catfish"
  },
  "spider": {
   "name": "거미",
   "atk": 5,
   "def": 2,
   "hp": 12,
   "spd": 3,
   "aps": 1.1,
   "portrait": "portrait_spider",
   "thorns": 2
  },
  "webmother": {
   "name": "거미 어미",
   "atk": 7,
   "def": 3,
   "hp": 20,
   "spd": 2,
   "aps": 1,
   "portrait": "portrait_webmother",
   "thorns": 4
  },
  "nestkeeper": {
   "name": "둥지 주인",
   "atk": 9,
   "def": 4,
   "hp": 34,
   "spd": 2,
   "aps": 0.9,
   "portrait": "portrait_nestkeeper",
   "thorns": 8
  },
  "hermit": {
   "name": "소라게",
   "atk": 6,
   "def": 3,
   "hp": 14,
   "spd": 2,
   "aps": 1,
   "portrait": "portrait_hermit",
   "shell": 3
  },
  "bigpincer": {
   "name": "큰 집게",
   "atk": 8,
   "def": 4,
   "hp": 22,
   "spd": 2,
   "aps": 0.9,
   "portrait": "portrait_bigpincer",
   "shell": 6
  },
  "cavekeeper": {
   "name": "동굴 주인",
   "atk": 10,
   "def": 5,
   "hp": 34,
   "spd": 2,
   "aps": 0.9,
   "portrait": "portrait_cavekeeper",
   "shell": 14
  },
  "rockmole": {
   "name": "바위 두더지",
   "atk": 5,
   "def": 2,
   "hp": 16,
   "spd": 3,
   "aps": 1.1,
   "portrait": "portrait_rockmole"
  },
  "cragram": {
   "name": "바위 산양",
   "atk": 7,
   "def": 3,
   "hp": 26,
   "spd": 4,
   "aps": 0.9,
   "portrait": "portrait_cragram"
  },
  "bigcentipede": {
   "name": "큰 지네",
   "atk": 8,
   "def": 4,
   "hp": 42,
   "spd": 3,
   "aps": 1,
   "portrait": "portrait_bigcentipede"
  },
  "cinderhound": {
   "name": "잿불 들개",
   "atk": 9,
   "def": 3,
   "hp": 30,
   "spd": 4,
   "aps": 1.1,
   "portrait": "portrait_cinderhound",
   "burn": 2
  },
  "ashboar": {
   "name": "잿불 멧돼지",
   "atk": 11,
   "def": 4,
   "hp": 48,
   "spd": 4,
   "aps": 0.8,
   "portrait": "portrait_ashboar",
   "burn": 3
  },
  "scorchstag": {
   "name": "그을린 사슴",
   "atk": 12,
   "def": 5,
   "hp": 75,
   "spd": 4,
   "aps": 0.9,
   "portrait": "portrait_scorchstag",
   "burn": 5
  },
  "cellarrat": {
   "name": "창고 쥐",
   "atk": 10,
   "def": 4,
   "hp": 26,
   "spd": 4,
   "aps": 1.2,
   "portrait": "portrait_cellarrat",
   "drain": 1
  },
  "gloombat": {
   "name": "큰 박쥐",
   "atk": 12,
   "def": 4,
   "hp": 40,
   "spd": 5,
   "aps": 1,
   "portrait": "portrait_gloombat",
   "drain": 3
  },
  "cellarkeeper": {
   "name": "창고 주인",
   "atk": 14,
   "def": 6,
   "hp": 85,
   "spd": 2,
   "aps": 0.9,
   "portrait": "portrait_cellarkeeper",
   "drain": 5
  },
  "towereye": {
   "name": "탑의 눈",
   "atk": 3,
   "def": 3,
   "hp": 90,
   "spd": 0,
   "aps": 0.4,
   "range": 15,
   "hits": 5,
   "move": "hold",
   "portrait": "portrait_towereye",
   "size": 2
  },
  "goldgolem": {
   "name": "황금 골렘",
   "atk": 14,
   "def": 6,
   "hp": 120,
   "spd": 0,
   "aps": 0.55,
   "move": "hold",
   "portrait": "portrait_goldgolem",
   "shell": 10,
   "size": 2
  }
 },
 "lands": [
  {
   "id": "mountain",
   "name": "산",
   "dungeon": false,
   "mob": "animal",
   "mid": "wolf",
   "boss": "bear"
  },
  {
   "id": "grassland",
   "name": "초원",
   "dungeon": false,
   "mob": "wilddog",
   "mid": "boar",
   "boss": "bison"
  },
  {
   "id": "forest",
   "name": "숲",
   "dungeon": false,
   "mob": "fox",
   "mid": "wolfleader",
   "boss": "forestbear"
  },
  {
   "id": "stonehide",
   "name": "돌가죽 굴",
   "dungeon": true,
   "mob": "stonebug",
   "mid": "shellback",
   "boss": "stonelord"
  },
  {
   "id": "swamptomb",
   "name": "늪지 무덤",
   "dungeon": true,
   "mob": "mosstoad",
   "mid": "bogarm",
   "boss": "tombkeeper"
  },
  {
   "id": "spidernest",
   "name": "거미 둥지",
   "dungeon": true,
   "mob": "spider",
   "mid": "webmother",
   "boss": "nestkeeper"
  },
  {
   "id": "shellcave",
   "name": "껍질 동굴",
   "dungeon": true,
   "mob": "hermit",
   "mid": "bigpincer",
   "boss": "cavekeeper"
  },
  {
   "id": "cellar",
   "name": "지하 창고",
   "dungeon": true,
   "mob": "cellarrat",
   "mid": "gloombat",
   "boss": "cellarkeeper"
  },
  {
   "id": "quarry",
   "name": "옛 채석장",
   "dungeon": false,
   "mob": "rockmole",
   "mid": "cragram",
   "boss": "bigcentipede"
  },
  {
   "id": "river",
   "name": "강가",
   "dungeon": false,
   "mob": "crayfish",
   "mid": "crocodile",
   "boss": "catfish"
  },
  {
   "id": "scorched",
   "name": "벼락 들판",
   "dungeon": false,
   "mob": "cinderhound",
   "mid": "ashboar",
   "boss": "scorchstag"
  },
  {
   "id": "towerruin",
   "name": "부서진 탑",
   "dungeon": false,
   "mob": null,
   "mid": null,
   "boss": "towereye"
  },
  {
   "id": "goldtower",
   "name": "무너진 금탑",
   "dungeon": false,
   "mob": null,
   "mid": null,
   "boss": "goldgolem"
  }
 ],
 "lv": {
  "atk": [
   0,
   0,
   0,
   0,
   0,
   1,
   1,
   1,
   1,
   1,
   2,
   2,
   2,
   2,
   2,
   3,
   3,
   3,
   3,
   3,
   4,
   4,
   4,
   4,
   4,
   5,
   5,
   5,
   5,
   5,
   6,
   6,
   6,
   6,
   6,
   7,
   7,
   7,
   7,
   7
  ],
  "def": [
   0,
   0,
   0,
   0,
   1,
   1,
   1,
   1,
   1,
   2,
   2,
   2,
   2,
   2,
   3,
   3,
   3,
   3,
   3,
   4,
   4,
   4,
   4,
   4,
   5,
   5,
   5,
   5,
   5,
   6,
   6,
   6,
   6,
   6,
   7,
   7,
   7,
   7,
   7,
   8
  ],
  "hp": [
   0,
   2,
   4,
   6,
   6,
   6,
   8,
   10,
   12,
   12,
   12,
   14,
   16,
   18,
   18,
   18,
   20,
   22,
   24,
   24,
   24,
   26,
   28,
   30,
   30,
   30,
   32,
   34,
   36,
   36,
   36,
   38,
   40,
   42,
   42,
   42,
   44,
   46,
   48,
   48
  ]
 },
 "armTag": {
  "melee": "근접무기",
  "axe": "도끼",
  "spear": "창",
  "bow": "원거리무기"
 }
};
