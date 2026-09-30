# Drill #8 — 애니메이션 뷰어

`animation_viewer.py`는 캐릭터 스프라이트 시트 하나에서 4종류의 애니메이션을 잘라내어
화면 중앙에서 순서대로 무한 반복 재생하는 pico2d 프로그램이다.

## 실행 방법

```
python animation_viewer.py
```

- ESC 키 또는 창 닫기(X 버튼)로 언제든 종료할 수 있다.

## 사용한 에셋

- `character_sheet.png` (482x470) — 번들로 제공된 "사막 폐허(Desert Ruins) 에셋 2종" 중 캐릭터 스프라이트 시트.
  - 설명: 24색 팔레트 · 2x 픽셀 스케일 · 모래 망토를 두른 소형 로봇 전사.
  - 별도의 외부 배포 URL이 확인되지 않아(로컬에 함께 제공된 미리보기 페이지 기준) 실제 웹 출처 대신
    번들에 포함된 설명을 그대로 밝힌다.

## 구현한 애니메이션

| 이름 | 프레임 수 |
|------|-----------|
| idle | 4 |
| walk | 6 |
| attack | 5 |
| jump | 3 |

각 애니메이션은 5회(`REPEAT_COUNT`) 반복 재생한 뒤 1초(`PAUSE_TIME`) 정지하고,
`ANIMATION_ORDER = ['idle', 'walk', 'attack', 'jump']` 순서대로 다음 애니메이션으로 넘어가며
전체를 무한히 순환한다. 캐릭터는 `SCALE = 4`배로 확대해서 그리며, 시트에서 가장 작은 프레임
기준으로도 화면 높이(600px) 절반인 300px을 넘도록(최소 프레임 90px x 4 = 360px) 설정했다.

## 가산점 구현 내용

### [가산점 A] 프레임마다 크기가 달라도 발 위치가 흔들리지 않게 처리

스프라이트 시트를 분석한 결과 프레임마다 폭과 높이가 제각각이다(예: jump 프레임은
90px, 120px, 94px로 높이가 다 다르다). `pico2d`의 `Image.clip_draw_to_origin(left, bottom,
width, height, x, y, w, h)`는 인자로 받은 `(x, y)`를 그릴 사각형의 **왼쪽 아래 꼭짓점**으로
사용한다. 만약 매 프레임마다 `CENTER_Y - draw_h // 2`처럼 프레임 높이에 따라 y를 다시 계산하면,
프레임 높이가 바뀔 때마다 캐릭터의 발(그림 아래쪽 끝)이 위아래로 흔들리게 된다.

이를 막기 위해 시트 전체에서 가장 높은 프레임(`max_frame_height`, 120px)을 기준으로 화면
세로 중앙에 캐릭터가 오도록 하는 y좌표를 딱 한 번 계산해서 `FOOT_Y` 상수로 고정했다.

```python
max_frame_height = max(h for frames in FRAMES.values() for (_, _, _, h) in frames)
FOOT_Y = CENTER_Y - (max_frame_height * SCALE) // 2
```

이후 `draw_character`는 프레임마다 폭(`draw_w`)에 따라 x만 다시 계산하고, y는 항상
`FOOT_Y`를 그대로 사용한다. 그 결과 프레임 높이가 90~120px로 달라져도 캐릭터의 발 높이는
항상 같은 자리에 고정되고, 캐릭터가 위로 자라나는 방향으로만 크기가 변한다.

### [가산점 B] 애니메이션마다 프레임 개수가 달라도 동작하는 일반화된 재생 로직

idle(4장) / walk(6장) / attack(5장) / jump(3장)처럼 애니메이션마다 프레임 개수가 전부
다르다. 이를 하드코딩된 반복 횟수 대신 데이터 중심으로 처리했다.

- `FRAMES`: 애니메이션 이름 → `(left, bottom, width, height)` 프레임 목록의 딕셔너리.
- `ANIMATION_ORDER`: 실제로 재생할 순서를 담은 리스트.

`play_animation(anim_name)` 함수는 `len(FRAMES[anim_name])`으로 프레임 개수를 그때그때
알아내기 때문에, 특정 애니메이션의 프레임이 몇 장이든 코드 수정 없이 그대로 동작한다.

```python
def play_animation(anim_name):
    frames = FRAMES[anim_name]
    for _ in range(REPEAT_COUNT):
        for frame_index in range(len(frames)):
            ...
```

메인 루프 역시 애니메이션 이름을 하드코딩하지 않고 `ANIMATION_ORDER`를 순회한다.

```python
while running:
    for anim_name in ANIMATION_ORDER:
        play_animation(anim_name)
```

따라서 애니메이션을 추가/삭제하거나 재생 순서를 바꾸고 싶으면 `FRAMES`와
`ANIMATION_ORDER`만 수정하면 되고, 재생 로직(`play_animation`, 메인 루프)은 전혀
손댈 필요가 없다.

## 종료 처리

`running` 플래그와 `handle_events()`로 창 닫기(SDL_QUIT)와 ESC 키(SDLK_ESCAPE) 입력을
매 프레임 확인한다. 애니메이션 사이 1초 정지도 `delay(1)`을 한 번에 호출하지 않고
`wait_seconds()`에서 0.05초 단위로 나눠 기다리면서 그때그때 이벤트를 처리하도록 구현해서,
정지 중에도 창이 멈춘 것처럼 보이지 않고 ESC/닫기 요청이 즉시 반영된다.
