"""캐릭터 · 크리처 아이콘 생성 — 기사 · 갓 · 토끼 · 곰 같은 인물과 생물.

슈퍼 데포르메(머리가 크고 몸이 작은) 비율 머리말이 붙음. 사물엔 쓰지 말 것 (사람이 끼어듦) → make_icon_object.py.
캐릭터는 얼굴 위주(`close-up face portrait, the head fills most of the frame, of ...`), 흰 배경(--bg white)이 잘 나옴.

사용법:
  python tools/make_icon_character.py --name card_knight --label 기사 --bg white --prompt "close-up face portrait, the head fills most of the frame, of a young knight ..."
  python tools/make_icon_character.py --name card_bear --label 곰 --prompt "full body of a big wild brown bear standing"
포트레이트(인스펙터 전신 그림)는 make_portrait.py.
"""
from icon_common import main

if __name__ == "__main__":
    main("character")
