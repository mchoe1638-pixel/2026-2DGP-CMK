from pico2d import *


open_canvas(800, 600)
grass = load_image('grass.png')
character = load_image('character.png')


def draw_frame(x, y):
    get_events()    # 창이 멈춘 것처럼 보이지 않도록 매 프레임 이벤트 처리
    clear_canvas()
    grass.draw(400, 30)
    character.draw(x, y)
    update_canvas()


# 사각형 이동 경로 범위 (왼쪽 아래 모서리에서 시작)
LEFT, RIGHT = 100, 700
BOTTOM, TOP = 100, 500
SPEED = 2

x, y = LEFT, BOTTOM
while True:
    while x < RIGHT:    # 오른쪽으로 이동
        draw_frame(x, y)
        x += SPEED
        delay(0.01)

    while y < TOP:       # 위쪽으로 이동
        draw_frame(x, y)
        y += SPEED
        delay(0.01)

    while x > LEFT:       # 왼쪽으로 이동
        draw_frame(x, y)
        x -= SPEED
        delay(0.01)

    while y > BOTTOM:      # 아래쪽으로 이동
        draw_frame(x, y)
        y -= SPEED
        delay(0.01)
