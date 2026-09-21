"""사물 아이콘 생성 — 재료 · 도구 · 무기 · 설비 · 음식 · 장소 · UI 그림.

사람 · 생물 · 손 · 얼굴이 끼지 않도록 앞(머리말)과 뒤(꼬리말)에 못 박아 둠. 프롬프트엔 그릴 사물만 적으면 됨.
캐릭터 · 크리처는 make_icon_character.py 를 쓸 것.

사용법:
  python tools/make_icon_object.py --name card_workbench --label 작업대 --prompt "a sturdy wooden crafting workbench with a vise"
  python tools/make_icon_object.py --name ui_shield --label "방패 실루엣" --no-style --bg white --prompt "a flat solid black silhouette of a kite shield"
옵션: --bg white (어두운 대상 · 불 · 금속) · --no-style (그림체 머리말 빼기, 실루엣 등) · --no-suffix · --seed · --force
"""
from icon_common import main

if __name__ == "__main__":
    main("object")
