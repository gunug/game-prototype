"""A포즈 마네킹 — 모든 캐릭터를 **같은 몸 틀** 위에 그려 머리 크기 · 키 · 팔 자리를 맞춘다 (2026-11-06).

make_apose.py 가 이 그림을 KREA2 img2img 의 시작 그림으로 쓴다 (얼굴 · 옷 · 색은 글이 정한다).
  adult : 어른 — 4.5등신, 키 880px
  child : 세리나 — 가렛보다 어린 아이, 3.6등신, 키 690px (머리 크기는 어른과 거의 같고 몸이 짧다)
발끝은 둘 다 같은 바닥선(y=950). 캔버스 768×1024, 밝은 회색 바탕 · 중간 회색 몸.

  python tools/apose_mannequin.py      # images/ref/mannequin_<kind>.png 를 다시 그린다
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

REF_DIR = Path(__file__).resolve().parent.parent / "images" / "ref"
W, H, FLOOR = 768, 1024, 950
BG, BODY, SHADE = (208, 208, 210), (150, 148, 150), (128, 126, 130)

# 몸 치수 — 머리 높이(head) 를 단위로 (heads = 등신)
KINDS = {
    "adult": dict(height=880, heads=4.5, shoulder=1.55, hip=1.05, limb=0.36, arm_out=0.42),
    "child": dict(height=690, heads=3.6, shoulder=1.25, hip=0.95, limb=0.33, arm_out=0.38),
}


def draw(kind):
    k = KINDS[kind]
    hd = k["height"] / k["heads"]                     # 머리 높이
    top = FLOOR - k["height"]
    cx = W / 2
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    hw = hd * 0.86                                    # 머리 폭
    d.ellipse([cx - hw / 2, top, cx + hw / 2, top + hd], fill=BODY)
    neck_y = top + hd * 0.95
    d.rectangle([cx - hd * 0.16, neck_y - hd * 0.1, cx + hd * 0.16, neck_y + hd * 0.18], fill=BODY)
    sh_y = neck_y + hd * 0.15                         # 어깨 선
    sw = hd * k["shoulder"] / 2
    hip_y = top + hd * (k["heads"] * 0.55)            # 엉덩이 선 (키의 반 남짓)
    hp = hd * k["hip"] / 2
    d.polygon([(cx - sw, sh_y), (cx + sw, sh_y), (cx + hp, hip_y), (cx - hp, hip_y)], fill=BODY)
    d.ellipse([cx - sw - hd * 0.12, sh_y - hd * 0.05, cx - sw + hd * 0.3, sh_y + hd * 0.35], fill=BODY)   # 어깨 둥글게
    d.ellipse([cx + sw - hd * 0.3, sh_y - hd * 0.05, cx + sw + hd * 0.12, sh_y + hd * 0.35], fill=BODY)
    # 팔 — 어깨에서 비스듬히 아래로 (A포즈). 손끝은 엉덩이보다 조금 아래
    lw = hd * k["limb"]
    hand_y = hip_y + hd * 0.45
    for s in (-1, 1):
        x0, x1 = cx + s * (sw - lw * 0.3), cx + s * (sw + hd * k["arm_out"])
        d.line([(x0, sh_y + lw * 0.4), (x1, hand_y)], fill=BODY, width=int(lw))
        d.ellipse([x1 - lw * 0.62, hand_y - lw * 0.3, x1 + lw * 0.62, hand_y + lw * 0.95], fill=BODY)   # 손
    # 다리 — 조금 벌리고 선다
    lg = hd * k["limb"] * 1.25
    for s in (-1, 1):
        xt, xb = cx + s * hp * 0.5, cx + s * hp * 0.62
        d.line([(xt, hip_y - lg * 0.3), (xb, FLOOR - lg * 0.35)], fill=BODY, width=int(lg))
        d.ellipse([xb - lg * 0.62, FLOOR - lg * 0.75, xb + lg * 0.62 + s * lg * 0.1, FLOOR], fill=SHADE)   # 발
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    REF_DIR.mkdir(parents=True, exist_ok=True)
    out = REF_DIR / f"mannequin_{kind}.png"
    im.save(out, optimize=True)
    return out


if __name__ == "__main__":
    for kd in KINDS:
        print(draw(kd))
