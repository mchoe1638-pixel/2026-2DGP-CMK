from pico2d import *

# TUK_GROUND.png 의 실제 크기가 1280 x 1024 이므로 캔버스도 같은 크기로 연다.
TUK_WIDTH, TUK_HEIGHT = 1280, 1024
open_canvas(TUK_WIDTH, TUK_HEIGHT)

tuk_ground = load_image('TUK_GROUND.png')
character = load_image('animation_sheet.png')


def handle_events():
    global running
    global x, y

    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_MOUSEMOTION:
            # event.x, event.y 는 윈도우 API 좌표계(왼쪽 위가 원점, y가 아래로 증가).
            # pico2d 는 왼쪽 아래가 원점이고 y가 위로 증가하므로 y를 뒤집어 준다.
            x, y = event.x, TUK_HEIGHT - 1 - event.y
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False


running = True
frame = 0
x, y = TUK_WIDTH // 2, TUK_HEIGHT // 2
hide_cursor()

while running:
    clear_canvas()

    tuk_ground.draw(TUK_WIDTH // 2, TUK_HEIGHT // 2)
    # animation_sheet.png 은 802 x 402, 프레임 한 칸이 100 x 100.
    # frame * 100 = 가로 위치, 100 * 1 = action 1번 행(세로 위치)
    character.clip_draw(frame * 100, 100 * 1, 100, 100, x, y)

    update_canvas()
    handle_events()
    frame = (frame + 1) % 8
    delay(0.05)

close_canvas()
