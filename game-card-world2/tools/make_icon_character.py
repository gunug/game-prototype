"""캐릭터 · 크리처 아이콘 생성 — 사람(기사 · 궁수 · 장인)과 생물(토끼 · 곰 · 거미).

그림 틀은 둘뿐이다 (docs/게임_규칙.md '캐릭터와 크리처'):
  --frame person    사람 카드 — **얼굴과 깃까지만**. 손도 연장도 넣지 않는다. 전신은 make_portrait.py 로 따로.
  --frame creature  크리처 — 얼굴만 따로 뽑지 않는다. **전신** 하나로 카드에도 필드에도 쓴다.

사물엔 쓰지 말 것 (사람이 끼어듦) → make_icon_object.py.

사용법:
  python tools/make_icon_character.py --name card_knight --label 기사 --frame person --bg white --prompt "a young knight with a scarred brow"
  python tools/make_icon_character.py --name card_bear  --label 곰   --frame creature --prompt "a big wild brown bear"
포트레이트(인스펙터 전신 그림)는 make_portrait.py --kind character|creature.
"""
from icon_common import main

if __name__ == "__main__":
    main("character")
