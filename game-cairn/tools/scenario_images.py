"""블러드 올름 시나리오 그림 한 벌 — make_image.py (ComfyUI Krea2 turbo) 로 없는 것만 뽑는다.

    python tools/scenario_images.py            # 없는 것만
    python tools/scenario_images.py --only c3_hive olm
    python tools/scenario_images.py --force    # 전부 다시

결과: images/scene/<id>.jpg (품질 88 — PNG 는 장당 1MB 넘어 웹에 무거움) — 안내 페이지(index.html) 시나리오 탭이 쓴다.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
STYLE = ("Dark fantasy illustration in gritty ink lines and muted painted color, old-school tabletop RPG book art, "
         "moody lighting, no text, no letters, no frame, no watermark. ")
WIDE, TALL, SQ = (1024, 704), (768, 1024), (896, 896)

# (id, 크기, 시드, 영어 묘사)
SHOTS = [
    # ── 방 ──
    ("c1_camp", WIDE, 111, "An abandoned explorers' campsite sheltered beneath a rock ledge in a narrow river canyon. "
     "Two open wooden crates beside a cold dead campfire of grey ashes and charred sticks with no flame and no smoke, one crate full of rotting reddish gourd-like fruit buzzing with flies. "
     "A small freshly dug tunnel in the muddy earth with a rope ladder tied to iron pitons. Four soggy moldy blankets laid out. "
     "Muddy footprints lead downhill. Late afternoon light, long shadows."),
    ("c2_entrance", WIDE, 12, "A large vertical cave mouth in a canyon wall, its lip ringed with vivid blue moss. "
     "Dead river weeds, shells and flat smooth stones scattered on the ground, old water lines on the rock showing the river once covered it. "
     "A ring of mud in front of the dark entrance. Muddy footprints going in."),
    ("c3_hive", WIDE, 13, "Inside a suffocating cave chamber: three fat dead dog-sized pale worm creatures with stubby legs and antler-like tubes on their heads lie on the floor. "
     "A pile of glistening egg sacks heaped in a corner. A large hot vent in the floor hisses gas, the air shimmering. "
     "A single torch flame in the foreground flickering eerie blue."),
    ("c4_ambush", WIDE, 14, "A tight cave corridor with a very high ceiling and sandy floor. Two large boulders dragged together form a narrow gap in the middle, drag marks in the sand. "
     "Above, jagged stalactites and dark rock ledges on both walls, one stalactite half broken. Gas makes the torchlight flicker blue. Ominous."),
    ("c5_ladder", WIDE, 15, "A muddy cave room where a rope ladder dangles from a round hole in the ceiling. A small rusted iron box sits in a corner. "
     "Dead fish stick out of the wet mud floor. White guano-flecked boot prints cross the room. Torchlight."),
    ("c6_bats", WIDE, 16, "A foul cave chamber, hundreds of bats clinging to long stalactites on the ceiling. "
     "The floor is a mess of white guano and rotten brown fruit with webbed footprints. "
     "On the far wall a large white fungus grows in thick hanging ropes, half hiding a small crawl tunnel."),
    ("c7_atrium", WIDE, 117, "An enormous cavern. A huge tree hangs UPSIDE DOWN from the cave ceiling: its trunk attached to the rock ceiling at the top of the picture, "
     "its crown of withered branches pointing downward, and its bare gnarled roots dangling down toward the floor, almost touching a pool. "
     "A small shallow pool on the sloped floor below with rotten fruit floating. Two still human bodies lie face-down far away near the wall, in shadow. Awe and decay."),
    ("c8_den", WIDE, 18, "A warm cramped humid cave den with walls of packed mud painted in bright swirls of color, primitive murals. "
     "A dozen small pale pink blind salamander-like cave creatures huddle together sleeping and whispering, some sickly and still. "
     "In a corner a clear bubbling spring is held back by a waist-high mud wall."),
    ("c9_lair", WIDE, 19, "A cave lair with freshly carved smooth mud walls wet with condensation. On the north side a wall of packed mud dams an underground river, water seeping through cracks. "
     "Scattered bones and remains of small creatures on the floor. Three pale gaunt eyeless predators sleep curled in the dark. Menacing."),
    ("c10_refuge", WIDE, 20, "A small circular cave chamber with perfectly smooth mud walls. A determined young teenage girl, mud-spattered, crouches on the floor "
     "pointing a spade toward the entrance, in her other hand a palm-sized crescent moon-shaped stone. Lit by a torch from the doorway."),
    ("c11_well", WIDE, 21, "The bottom of an ancient dry stone well, a round room with stone walls and a great shaft rising into darkness above. "
     "A pile of refuse pushed to one side: an old metal pail, a set of small delicate porcelain cups, and an old human skeleton. "
     "A bolt of canvas draped over a stone slab as a bed. A thin shaft of light from far above."),
    # ── 인물 · 짐승 ──
    ("olm", TALL, 31, "Full body portrait of a peaceful Olm: a small pale pink blind cave-dwelling humanoid salamander creature with smooth skin, "
     "tiny vestigial eye spots, feathery pink gills, long thin limbs, crouching gently on a wet cave rock. Calm, harmless, sickly thin."),
    ("tube_worm", SQ, 32, "A dog-sized blind herbivore cave worm creature with a fat pale segmented body, short stubby legs, "
     "and branching antler-like tubes growing from its head. Standing on a wet cave floor. Strange but not scary."),
    ("geteli", TALL, 33, "Full body portrait of High Lector Geteli: a lanky haughty middle-aged scholar gone insane, "
     "ragged once-fine scholar robes caked with mud, deep crimson eyes, wild unkempt hair, gripping a sharpened iron piton as a weapon. "
     "Lurking on a cave ledge in shadow. Madness."),
    ("jhel_fries", TALL, 134, "Full body portrait of Jhel-Fries: a resourceful fifteen-year-old local girl with a long dark braid, an experienced cave diver, "
     "practical patched tunic and trousers, mud-spattered face and arms, holding a small spade. Wary but brave. Cave background."),
    # ── 물건 ──
    ("mud_sieve", SQ, 41, "A relic called the Mud Sieve: a palm-sized crescent moon-shaped smooth grey stone with faint carved lines, "
     "lying on wet dark mud that subtly ripples around it like water. Close-up still life, magical."),
    ("red_hermit_fruit", SQ, 42, "Still life of a fresh Red Hermit fruit: a gourd-like deep red fruit with a glossy skin, sweet and juicy, "
     "next to a rotting brown one, on a cave rock. Close-up."),
]


def main():
    args = sys.argv[1:]
    force = "--force" in args
    only = set(args[args.index("--only") + 1:]) if "--only" in args else None
    out = ROOT / "images" / "scene"
    for sid, (w, h), seed, desc in SHOTS:
        if only and sid not in only:
            continue
        if (out / f"{sid}.jpg").exists() and not force and not only:
            print("있음", sid)
            continue
        cmd = [sys.executable, str(ROOT / "tools" / "make_image.py"), "--name", sid,
               "--w", str(w), "--h", str(h), "--seed", str(seed), "--prompt", STYLE + desc]
        subprocess.run(cmd, check=True)
        png = out / f"{sid}.png"
        Image.open(png).convert("RGB").save(out / f"{sid}.jpg", quality=88, optimize=True)
        png.unlink()


if __name__ == "__main__":
    main()
