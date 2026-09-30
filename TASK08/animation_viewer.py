# Drill #8: 애니메이션 뷰어
# 캐릭터 스프라이트 시트에서 애니메이션을 읽어와 화면 중앙에서 재생한다.
from pico2d import *

SCREEN_W, SCREEN_H = 800, 600
CENTER_X = SCREEN_W // 2
CENTER_Y = SCREEN_H // 2

open_canvas(SCREEN_W, SCREEN_H)

# 스프라이트 시트(character_sheet.png, 482x470)를 PIL로 분석해서 얻은 프레임 좌표.
# (left, bottom, width, height) : pico2d 이미지 좌표계(원점이 왼쪽 아래)를 기준으로 한다.
FRAMES = {
    'idle': [
        (8, 362, 62, 100),
        (78, 362, 64, 100),
        (150, 362, 66, 98),
        (224, 362, 64, 98),
    ],
    'walk': [
        (8, 254, 70, 98),
        (86, 254, 74, 100),
        (168, 254, 72, 100),
        (248, 254, 72, 98),
        (328, 254, 68, 100),
        (404, 254, 70, 100),
    ],
    'attack': [
        (8, 136, 68, 98),
        (84, 136, 56, 110),
        (148, 136, 96, 104),
        (252, 136, 84, 100),
        (344, 136, 80, 100),
    ],
    'jump': [
        (8, 8, 72, 90),
        (88, 8, 44, 120),
        (140, 8, 94, 94),
    ],
}

character = load_image('character_sheet.png')

SCALE = 4  # 캐릭터를 화면 높이 절반 이상으로 키우기 위한 확대 배율
REPEAT_COUNT = 5   # 애니메이션 하나를 반복할 횟수
PAUSE_TIME = 1.0   # 애니메이션 사이 정지 시간(초)
PAUSE_STEP = 0.05  # 정지 중 이벤트를 확인하는 간격(초)


def draw_character(anim_name, frame_index):
    # 지정한 애니메이션의 frame_index번째 프레임을 화면 중앙에 그린다.
    # clip_draw_to_origin은 (x, y)가 그릴 사각형의 왼쪽 아래 기준이라
    # 중앙에 두려면 그릴 크기의 절반만큼 x, y를 보정해야 한다.
    left, bottom, width, height = FRAMES[anim_name][frame_index]
    draw_w, draw_h = width * SCALE, height * SCALE
    character.clip_draw_to_origin(
        left, bottom, width, height,
        CENTER_X - draw_w // 2, CENTER_Y - draw_h // 2,
        draw_w, draw_h
    )


def wait_seconds(seconds):
    # delay(seconds)로 한 번에 멈추지 않고 짧은 간격(PAUSE_STEP)으로 나눠 기다린다.
    # 그 사이에도 get_events()를 호출해서 Windows에서 창이 '응답 없음' 상태가 되지 않게 한다.
    elapsed = 0.0
    while elapsed < seconds:
        get_events()
        delay(PAUSE_STEP)
        elapsed += PAUSE_STEP


# idle -> walk -> attack -> jump 를 무한히 순환 재생한다.
while True:
    for _ in range(REPEAT_COUNT):
        for i in range(len(FRAMES['idle'])):
            clear_canvas()
            draw_character('idle', i)
            update_canvas()
            delay(0.1)
    wait_seconds(PAUSE_TIME)

    for _ in range(REPEAT_COUNT):
        for i in range(len(FRAMES['walk'])):
            clear_canvas()
            draw_character('walk', i)
            update_canvas()
            delay(0.1)
    wait_seconds(PAUSE_TIME)

    for _ in range(REPEAT_COUNT):
        for i in range(len(FRAMES['attack'])):
            clear_canvas()
            draw_character('attack', i)
            update_canvas()
            delay(0.1)
    wait_seconds(PAUSE_TIME)

    for _ in range(REPEAT_COUNT):
        for i in range(len(FRAMES['jump'])):
            clear_canvas()
            draw_character('jump', i)
            update_canvas()
            delay(0.1)
    wait_seconds(PAUSE_TIME)

close_canvas()
