# Drill #8: 애니메이션 뷰어
# 캐릭터 스프라이트 시트에서 idle, walk, attack, jump 네 가지 애니메이션을 읽어와
# 화면 중앙에서 순서대로 무한 반복 재생한다.
# 각 애니메이션은 5회 반복 후 1초 정지하고 다음 애니메이션으로 넘어간다.
from pico2d import *

# 화면/배치 설정
SCREEN_W, SCREEN_H = 800, 600
CENTER_X = SCREEN_W // 2
CENTER_Y = SCREEN_H // 2

open_canvas(SCREEN_W, SCREEN_H)

# 애니메이션 프레임 데이터
# character_sheet.png(482x470)를 PIL로 분석해서 얻은 프레임 좌표.
# (left, bottom, width, height) : pico2d 이미지 좌표계(원점이 왼쪽 아래)를 기준으로 한다.
# [가산점 B] 애니메이션마다 프레임 개수가 달라도(4/6/5/3개) 아래 재생 로직은 그대로 동작한다.
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

# 재생 순서. 이 리스트만 바꾸면 애니메이션 순서나 개수를 바꿀 수 있다.
ANIMATION_ORDER = ['idle', 'walk', 'attack', 'jump']

# 재생 타이밍 설정
SCALE = 4          # 가장 작은 프레임(90px)도 화면 높이 절반(300px)을 넘도록 하는 확대 배율
REPEAT_COUNT = 5   # 애니메이션 하나를 반복할 횟수
FRAME_TIME = 0.1   # 프레임 하나가 유지되는 시간(초)
PAUSE_TIME = 1.0   # 애니메이션 사이 정지 시간(초)
PAUSE_STEP = 0.05  # 정지 중 이벤트를 확인하는 간격(초)

# [가산점 A] 프레임마다 높이가 달라도(90~120px) 발 위치가 흔들리지 않도록,
# 시트에서 가장 높은 프레임을 기준으로 화면 세로 중앙에 오는 발 위치를 미리 계산해 둔다.
max_frame_height = max(h for frames in FRAMES.values() for (_, _, _, h) in frames)
FOOT_Y = CENTER_Y - (max_frame_height * SCALE) // 2

character = load_image('character_sheet.png')

running = True

def handle_events():
    # 이벤트를 처리하고, 창 닫기나 ESC 입력이 있으면 running을 꺼서 재생을 멈춘다.
    global running
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False

def draw_character(anim_name, frame_index):
    # anim_name의 frame_index번째 프레임을 화면 중앙, 고정된 발 위치(FOOT_Y)에 그린다.
    # clip_draw_to_origin(left, bottom, w, h, x, y, w, h)은 (x, y)가 그릴 사각형의
    # '왼쪽 아래' 기준이라서, x는 가로 중앙에 오도록 캐릭터 폭의 절반만큼 보정하고
    # y는 프레임 크기와 상관없이 항상 FOOT_Y를 그대로 사용해 발 높이를 고정한다.
    left, bottom, width, height = FRAMES[anim_name][frame_index]
    draw_w, draw_h = width * SCALE, height * SCALE
    character.clip_draw_to_origin(
        left, bottom, width, height,
        CENTER_X - draw_w // 2, FOOT_Y,
        draw_w, draw_h
    )

def wait_seconds(seconds):
    # delay(seconds)로 한 번에 멈추지 않고 짧은 간격(PAUSE_STEP)으로 나눠 기다린다.
    # 그 사이에도 이벤트를 계속 처리해서 Windows에서 창이 '응답 없음' 상태가 되지 않고,
    # ESC/닫기 요청도 정지 중에 바로 반영되게 한다.
    elapsed = 0.0
    while elapsed < seconds and running:
        handle_events()
        delay(PAUSE_STEP)
        elapsed += PAUSE_STEP

def play_animation(anim_name):
    # anim_name 애니메이션을 REPEAT_COUNT번 반복 재생한 뒤 PAUSE_TIME만큼 정지한다.
    # 프레임 개수는 FRAMES[anim_name]의 길이를 그대로 쓰므로 애니메이션마다 달라도 된다.
    frames = FRAMES[anim_name]
    for _ in range(REPEAT_COUNT):
        if not running:
            return
        for frame_index in range(len(frames)):
            clear_canvas()
            draw_character(anim_name, frame_index)
            update_canvas()
            handle_events()
            if not running:
                return
            delay(FRAME_TIME)
    wait_seconds(PAUSE_TIME)

while running:
    for anim_name in ANIMATION_ORDER:
        play_animation(anim_name)
        if not running:
            break

close_canvas()
