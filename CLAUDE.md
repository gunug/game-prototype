# game-prototype

## 기능 관리 규칙

모든 기능 요청은 **각 게임 폴더의 `docs/기능.md`** 로 관리한다.
(`game-card/docs/기능.md`, `game-exact-cover/docs/기능.md`,
`game-drag-drop/docs/기능.md` …)

작업 순서:

1. 작업 전 해당 게임의 `docs/기능.md`를 읽는다.
2. 코드를 수정한다.
3. 수정한 내용을 그 게임의 `docs/기능.md`에 기록한다.
4. **구현이 끝난 항목은 반드시 그 자리에서 체크박스를 `- [x]`로 바꾸고, 코드와 같은 커밋에 담는다.**
   - 검증까지 끝난 항목만 체크한다. 부분 구현이면 체크하지 않고 무엇이 남았는지 답변에 적는다.
   - 스펙에 없던 판단(범위·기본값 등)을 했다면 해당 항목 아래에 한 줄로 남긴다.

새 게임을 만들 때는 `<게임>/docs/기능.md` 를 먼저 만들고 시작한다.

사용자가 `기능.md`를 거치지 않고 그냥 요청하는 경우:

- 먼저 해당 게임의 `기능.md`에 항목으로 기록한 뒤 작업한다.
- 또는 사용자에게 `기능.md`에 먼저 기록할 것을 권장한다.

## 이미지 생성 (game-card-world2)

ComfyUI(`http://127.0.0.1:8188`) 아이콘은 **그릴 대상에 따라 스크립트를 골라** 쓴다. 섞어 쓰면 사물에 사람이 끼거나 캐릭터 비율이 틀어진다.

| 그릴 것 | 스크립트 | 비고 |
|---|---|---|
| 사물 · 재료 · 도구 · 무기 · 방어구 · 설비 · 음식 · 장소 · UI 그림 | `game-card-world2/tools/make_icon_object.py` | 사람 · 생물 · 손 · 얼굴이 안 끼게 머리말 · 꼬리말에 박혀 있음. 프롬프트엔 사물만 |
| 캐릭터 · 크리처 (기사 · 갓 · 토끼 · 곰 …) | `game-card-world2/tools/make_icon_character.py` | 슈퍼 데포르메 인물 비율 머리말. 캐릭터는 얼굴 위주 + `--bg white` |
| 인스펙터 전신 포트레이트 | `game-card-world2/tools/make_portrait.py --kind character·creature·place` | `place`는 사물용 머리말을 씀 |

- 공통 부분은 `tools/icon_common.py` (직접 실행 안 함).
- 사용: `python tools/make_icon_object.py --name <분류>_<id> --label <한글> --prompt "<영문>"` — 분류는 `card` · `tag` · `status` · `ui` · `fx`, card 의 id 는 `index.html` DEFS 키.
- 어두운 대상 · 불 · 금속 · 실루엣은 `--bg white`. 납작한 실루엣 등 그림체를 빼려면 `--no-style`.
- 성공하면 `docs/아이콘_목록.md`에 파일명 · seed · 옵션(`(object)`/`(character)`) · 프롬프트가 자동 기록된다.
- 뽑은 뒤 64px 결과를 확대해 눈으로 확인하고(사람이 끼었는지, 배경 잔여물) 커밋한다.
