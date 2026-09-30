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

SCALE = 4          # 캐릭터를 화면 높이 절반 이상으로 키우기 위한 확대 배율
REPEAT_COUNT = 5   # 애니메이션 하나를 반복할 횟수
PAUSE_TIME = 1.0   # 애니메이션 사이 정지 시간(초)
PAUSE_STEP = 0.05  # 정지 중 이벤트를 확인하는 간격(초)

# [가산점A] 프레임마다 높이가 달라도(90~120px) 발 위치가 흔들리지 않도록,
# 시트에서 가장 높은 프레임을 기준으로 화면 세로 중앙에 오는 발 위치를 미리 계산해 둔다.
max_frame_height = max(h for frames in FRAMES.values() for (_, _, _, h) in frames)
FOOT_Y = CENTER_Y - (max_frame_height * SCALE) // 2


def draw_character(anim_name, frame_index):
    # anim_name의 frame_index번째 프레임을 화면 중앙, 고정된 발 위치(FOOT_Y)에 그린다.
    # clip_draw_to_origin의 (x, y)는 그릴 사각형의 왼쪽 아래 기준이라서,
    # y는 프레임 크기와 상관없이 항상 FOOT_Y를 그대로 사용해 발 높이를 고정한다.
    left, bottom, width, height = FRAMES[anim_name][frame_index]
    draw_w, draw_h = width * SCALE, height * SCALE
    character.clip_draw_to_origin(
        left, bottom, width, height,
        CENTER_X - draw_w // 2, FOOT_Y,
        draw_w, draw_h
    )


running = True

def handle_events():
    # 이벤트를 처리하고, 창 닫기나 ESC 입력이 있으면 running을 꺼서 재생을 멈춘다.
    global running
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False


def wait_seconds(seconds):
    # delay(seconds)로 한 번에 멈추지 않고 짧은 간격(PAUSE_STEP)으로 나눠 기다린다.
    elapsed = 0.0
    while elapsed < seconds and running:
        handle_events()
        delay(PAUSE_STEP)
        elapsed += PAUSE_STEP


while running:
    for _ in range(REPEAT_COUNT):
        if not running:
            break
        for i in range(len(FRAMES['idle'])):
            clear_canvas()
            draw_character('idle', i)
            update_canvas()
            handle_events()
            if not running:
                break
            delay(0.1)
    wait_seconds(PAUSE_TIME)

    for _ in range(REPEAT_COUNT):
        if not running:
            break
        for i in range(len(FRAMES['walk'])):
            clear_canvas()
            draw_character('walk', i)
            update_canvas()
            handle_events()
            if not running:
                break
            delay(0.1)
    wait_seconds(PAUSE_TIME)

    for _ in range(REPEAT_COUNT):
        if not running:
            break
        for i in range(len(FRAMES['attack'])):
            clear_canvas()
            draw_character('attack', i)
            update_canvas()
            handle_events()
            if not running:
                break
            delay(0.1)
    wait_seconds(PAUSE_TIME)

    for _ in range(REPEAT_COUNT):
        if not running:
            break
        for i in range(len(FRAMES['jump'])):
            clear_canvas()
            draw_character('jump', i)
            update_canvas()
            handle_events()
            if not running:
                break
            delay(0.1)
    wait_seconds(PAUSE_TIME)

close_canvas()
