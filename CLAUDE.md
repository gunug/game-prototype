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
| **캐릭터 — 사람과 크리처 전부** | `game-card-world2/tools/make_character_sheet.py --kind person|creature` | **KREA2 체인 + BiRefNet-HR** 워크플로우. 한 번에 얼굴 · 상반신 · 전신 세 장을 뽑아 제 자리에 넣는다 |
| 땅 · 설비 포트레이트 | `game-card-world2/tools/make_portrait.py --kind place` | 사물용 머리말. 사람 · 크리처에는 더 쓰지 않는다 (위 스크립트가 맡는다) |

### 캐릭터 그림 — 세 장 한 벌 (2026-10-06 확정)

사람이든 크리처든 **`make_character_sheet.py` 하나로만** 뽑는다. 한 번 돌리면 세 장이 제 자리에 들어간다.

| 단계 | 파일 | 규격 | 쓰이는 곳 |
|---|---|---|---|
| 얼굴 | `images/icon/card_<id>.png` | 64×64 · 32색 | 카드 |
| 상반신 | `images/portrait/bust_<id>.png` | 192×256 | 인스펙터 |
| 전신 | `images/portrait/portrait_<id>.png` | 192×256 | 전투 (줄에 서는 그림) |

```bash
python tools/make_character_sheet.py --name archer --kind person --label 궁수     --desc "a young woman archer in a green hooded cloak ..."
```

- 그림체는 워크플로우 기본 톤(AAA western key art · semi-realistic oil painting)으로 **스크립트에 박혀 있다**. `--desc` 엔 그 캐릭터 묘사만 적는다.
- **크리처는 `--kind creature` 를 반드시 준다** — 사람 · 인간형 · 손 · 옷 · 무기가 끼지 않게 단계마다 못을 박고, 전신은 **왼쪽을 보게** 그린다 (원정이 왼→오른쪽이라 기다리는 쪽이 왼쪽을 본다). 좌우가 같은 꼴(거미 · 게 · 두꺼비)은 정면도 좋다. 이미 뽑은 그림이 반대면 좌우를 뒤집는다.
- 틀이 맘에 안 들면 다시 뽑지 말고 크롭 손잡이만 돌린다 — `--face-pad`(크면 얼굴에서 멀어짐) · `--upper-pad` · `--upper-down` · `--face-down`. 같은 `--seed` 면 그림은 그대로다.
- 구도가 맘에 안 들면 `--seed` 만 바꾼다. 한 벌에 약 70초, 한 단계만 다시 뽑으면(`--only face`) 약 8초.
- 얼굴이랄 것이 없어 얼굴 검출이 빗나가는 것(바위 등껍질 · 돌벌레 · 거미 · 소라게 …)은 `--card-from full` — 카드에 **전신**을 담아야 64px 에서 읽힌다.
- 원본 큰 그림(720×1280 · 720×1024 · 1024×1024, 투명본 포함)은 `ComfyUI/output/krea2_chain/` 에 남는다.
- 명단은 `tools/roster_characters.py` — 사람 9 · 크리처 25 의 id · 한글 이름 · 영문 묘사가 들어 있다. 한꺼번에 다시 뽑을 때 쓴다.

```bash
python tools/roster_characters.py            # 아직 얼굴 카드가 없는 것만
python tools/roster_characters.py --all      # 전부 (약 40분)
python tools/roster_characters.py --only wolf fox
```

- 공통 부분은 `tools/icon_common.py` (직접 실행 안 함).
- 원정 트랙 **배경 타일**은 `tools/make_bg_tile.py` — 배경을 지우지 않고 좌우 이음매를 섞어 가로로 이어 붙게 만든다. 기본 288×126 (한 칸 96px × 3칸). 결과는 `images/bg/bg_<땅id>.png`, 표는 `index.html` 의 `LANE_BG`.
  - **원경(`-far`)은 처음부터 세로로 길게** 뽑는다 — `--gen-w 1024 --gen-h 896 --out-w 576 --out-h 512 --kan 6`.
    화면은 비율을 지키려고 그림을 **바닥에 붙여** 폭만 칸에 맞추므로, 보이는 창은 **그림의 아래쪽**이고 줌아웃하면 위가 드러난다.
    그래서 프롬프트에 **경치·지평선은 맨 아래 1/4**, 위 3/4은 그 땅에 맞는 것(들판이면 하늘, 굴이면 천장과 어둠, 늪이면 안개)을 적는다. **하늘을 고정하지 않는다.**
    (`--sky-h` 는 맨 윗줄을 늘려 채우는 임시 수단 — 늘어져 보이므로 원경에는 쓰지 않는다.)
- 카드 **프레임**(테두리)은 `tools/make_frame.py` — 156×212, 워크플로우 `tools/card_frame_workflow.json`. 예: 보스 전용 `frame_boss`. 결과는 `images/frame/`.
- 사용: `python tools/make_icon_object.py --name <분류>_<id> --label <한글> --prompt "<영문>"` — 분류는 `card` · `tag` · `status` · `ui` · `fx`, card 의 id 는 `index.html` DEFS 키.
- 어두운 대상 · 불 · 금속 · 실루엣은 `--bg white`. 납작한 실루엣 등 그림체를 빼려면 `--no-style`.
- 성공하면 `docs/아이콘_목록.md`에 파일명 · seed · 옵션(`(object)`/`(character)`) · 프롬프트가 자동 기록된다.
- 뽑은 뒤 64px 결과를 확대해 눈으로 확인하고(사람이 끼었는지, 배경 잔여물) 커밋한다.

### UI 아이콘 (이모지 대신)

화면에 이모지를 직접 쓰지 않는다 — 기기마다 그림이 달라진다.

- 표: `index.html` 의 `ICONS` (id → 파일명) 하나뿐. 새 그림은 여기에 id 로 등록한다.
- 글 속 이모지는 `EMOJI_ICON` 표를 보고 `paintIcons()` 가 그림으로 바꿔 끼운다 (렌더 뒤 한 번).
- 새 UI 아이콘은 `tools/make_ui_icons.py` 에 (파일명 · 한글 이름 · 영문 프롬프트 · 흰 배경 여부) 한 줄을 더하고 실행하면 없는 것만 뽑는다.
- 파일명은 `ui_<id>.png`. 카드 그림을 그대로 쓰는 경우엔 `card_<id>.png` 를 `ICONS` 에 적는다.
