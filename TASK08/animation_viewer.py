# Drill #8: 애니메이션 뷰어
# 캐릭터 스프라이트 시트에서 애니메이션을 읽어와 화면 중앙에서 재생한다.
from pico2d import *

open_canvas(800, 600)

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


def draw_character(anim_name, frame_index):
    # 지정한 애니메이션의 frame_index번째 프레임을 SCALE배로 키워서 그린다.
    left, bottom, width, height = FRAMES[anim_name][frame_index]
    draw_w, draw_h = width * SCALE, height * SCALE
    character.clip_draw_to_origin(left, bottom, width, height, 400, 300, draw_w, draw_h)


frame_index = 0
while True:
    clear_canvas()
    draw_character('idle', frame_index)
    update_canvas()
    delay(0.1)
    frame_index = (frame_index + 1) % len(FRAMES['idle'])

close_canvas()
