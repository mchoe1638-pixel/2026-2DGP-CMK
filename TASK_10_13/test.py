from pico2d import *

open_canvas(800, 600)
background = load_image("grass.png")
character = load_image("animation_sheet.png")

COLS, ROWS = 8, 4
frame_w = character.w // COLS     # 100
frame_h = character.h // ROWS     # 100

x, y = 100, 100
dir_x, dir_y = 0, 0
speed = 5
face = 1          # 바라보는 방향: 1 = 오른쪽, -1 = 왼쪽
col = 0           # 동작의 몇 번째 그림인지 (0~7)
tick = 0          # 애니메이션 속도 조절용 카운터
running = True

while running:
    # 1) 입력
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN:
            if   event.key == SDLK_ESCAPE: running = False
            elif event.key == SDLK_RIGHT:  dir_x += 1
            elif event.key == SDLK_LEFT:   dir_x -= 1
            elif event.key == SDLK_UP:     dir_y += 1
            elif event.key == SDLK_DOWN:   dir_y -= 1
        elif event.type == SDL_KEYUP:
            if   event.key == SDLK_RIGHT:  dir_x -= 1
            elif event.key == SDLK_LEFT:   dir_x += 1
            elif event.key == SDLK_UP:     dir_y -= 1
            elif event.key == SDLK_DOWN:   dir_y += 1

    # 2) 업데이트
    x += dir_x * speed
    y += dir_y * speed

    if dir_x != 0:
        face = dir_x                  # 좌우 키를 누를 때만 바라보는 방향 갱신

    moving = (dir_x != 0 or dir_y != 0)
    if moving:                  # 움직이는 중
        if face == 1:
            row = 1             # 달리기 - 오른쪽
        else:
            row = 0             # 달리기 - 왼쪽
    else:                       # 멈춰 있음
        if face == 1:
            row = 3             # 서 있기 - 오른쪽
        else:
            row = 2             # 서 있기 - 왼쪽

    tick += 1
    if tick % 5 == 0:                 # 5루프마다 한 칸 → 초당 약 20칸
        col = (col + 1) % COLS

    # 3) 렌더링
    clear_canvas()
    background.draw(400, 50)
    character.clip_draw(col * frame_w, row * frame_h, frame_w, frame_h, x, y)
    update_canvas()
    delay(0.01)

close_canvas()