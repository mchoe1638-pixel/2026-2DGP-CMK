from pico2d import *


open_canvas(800, 600)
grass = load_image('grass.png')
character = load_image('character.png')


def handle_events():
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            return False
    return True


def draw_frame(x, y):
    clear_canvas()
    grass.draw(400, 30)
    character.draw(x, y)
    update_canvas()


# 사각형 이동 경로 범위 (왼쪽 아래 모서리에서 시작)
LEFT, RIGHT = 100, 700
BOTTOM, TOP = 100, 500
SPEED = 2

x, y = LEFT, BOTTOM
running = True
while running:
    while running and x < RIGHT:    # 오른쪽으로 이동
        running = handle_events()
        draw_frame(x, y)
        x += SPEED
        delay(0.01)

    while running and y < TOP:       # 위쪽으로 이동
        running = handle_events()
        draw_frame(x, y)
        y += SPEED
        delay(0.01)

    while running and x > LEFT:       # 왼쪽으로 이동
        running = handle_events()
        draw_frame(x, y)
        x -= SPEED
        delay(0.01)

    while running and y > BOTTOM:      # 아래쪽으로 이동
        running = handle_events()
        draw_frame(x, y)
        y -= SPEED
        delay(0.01)

close_canvas()
