from pico2d import*
open_canvas(800, 600)
background = load_image("grass.png")
character = load_image("animation_sheet.png")
COLS = 8
ROWS = 1
frame_w = character.w//COLS
frame_h = character.h//ROWS

col = 0
row = 0

spawn_x =100
spawn_y=100
dir_x, dir_y = 0,0
speed=5
running = True
while running:
    events = get_events()
    for event in events:
        if event.type==SDL_QUIT:
            running = False
        elif event.type==SDL_KEYDOWN:
            if event.type==SDLK_ESCAPE:
                running = False
            elif event.key == SDLK_RIGHT:
                dir_x+=1
            elif event.key == SDLK_LEFT:
                dir_x-=1
            elif event.key==SDLK_UP:
                dir_y+=1
            elif event.key==SDLK_DOWN:
                dir_y-=1
        elif event.type==SDL_KEYUP:
            if event.type==SDLK_ESCAPE:
                running = False
            elif event.key == SDLK_RIGHT:
                dir_x-=1
            elif event.key == SDLK_LEFT:
                dir_x+=1
            elif event.key==SDLK_UP:
                dir_y-=1
            elif event.key==SDLK_DOWN:
                dir_y+=1
    spawn_x += dir_x * speed
    spawn_y += dir_y*speed

    clear_canvas()
    background.draw(400, 50)
    character.clip_draw(col * frame_w, row*frame_h, frame_w, frame_h, spawn_x, spawn_y)
    col = (col+1)%COLS
    row = (row+1)%ROWS
    update_canvas()
    delay(0.01)
    pass
close_canvas()