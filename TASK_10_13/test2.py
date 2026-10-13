from pico2d import*
open_canvas(800, 600)
background = load_image("grass.png")
character = load_image("animation_sheet.png")

running  = True
spawn_x, spawn_y = 100, 100

dir_x, dir_y = 0,0

face = 1

col, row = 0,0

speed = 5

tick = 0

COLS = 8
ROWS = 4

frame_w = character.w//COLS
frame_h = character.h//ROWS

col, row = 0, 0

while running:
    #입력
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE: running = False
            elif event.key == SDLK_RIGHT: dir_x += 1
            elif event.key == SDLK_LEFT: dir_x -= 1
            elif event.key == SDLK_UP: dir_y += 1
            elif event.key == SDLK_DOWN: dir_y -= 1
        elif event.type == SDL_KEYUP:
            if event.key == SDLK_RIGHT: dir_x -= 1
            elif event.key == SDLK_LEFT: dir_x += 1
            elif event.key == SDLK_UP: dir_y -= 1
            elif event.key == SDLK_DOWN: dir_y += 1
    #업데이트
    spawn_x += dir_x*speed
    spawn_y += dir_y*speed
    if dir_x != 0:
        face = dir_x
    moving = (dir_x != 0 or dir_y != 0)
    if moving:
        if face == 1:
            row = 1
        else: 
            row = 0
    else:
        if face == 1:
            row = 3
        else:
            row = 2
    tick += 1
    if tick % 5 == 0:
        col = (col + 1) % COLS

    #렌더링
    clear_canvas()
    background.draw(400, 40)
    character.clip_draw(col*frame_w, row*frame_h, frame_w, frame_h, spawn_x, spawn_y)
    update_canvas()
    delay(0.01)

close_canvas()
