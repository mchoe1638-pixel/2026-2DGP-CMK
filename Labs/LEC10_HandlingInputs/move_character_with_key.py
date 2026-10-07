from pico2d import *


open_canvas()
grass = load_image('grass.png')
character = load_image('animation_sheet.png')


def handle_events():
    global running, dir_x, dir_y, face

    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False

        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_d:
                dir_x += 2
            elif event.key == SDLK_a:
                dir_x -= 2
            elif event.key == SDLK_w:
                dir_y += 2
            elif event.key == SDLK_s:
                dir_y -= 2
            elif event.key == SDLK_ESCAPE:
                running = False

        elif event.type == SDL_KEYUP:
            if event.key == SDLK_d:
                dir_x -= 2
            elif event.key == SDLK_a:
                dir_x += 2
            elif event.key == SDLK_w:
                dir_y -= 2
            elif event.key == SDLK_s:
                dir_y += 2

    # 좌우 입력이 있으면 바라보는 방향 갱신
    if dir_x > 0:
        face = 1      # 오른쪽
    elif dir_x < 0:
        face = 0      # 왼쪽


running = True
x = 800 // 2
y = 90
frame = 0
dir_x = 0     # -1: 왼쪽, 0: 정지, 1: 오른쪽
dir_y = 0     # -1: 아래, 0: 정지, 1: 위
face = 1      # 1: 오른쪽 보기, 0: 왼쪽 보기
speed = 5

while running:
    clear_canvas()
    grass.draw(400, 30)

    # 스프라이트 시트: 아래 줄(y=0)이 왼쪽 달리기, 그 위(y=100)가 오른쪽 달리기
    character.clip_draw(frame * 100, 100 * face, 100, 100, x, y)
    update_canvas()

    handle_events()

    # 움직일 때만 애니메이션 진행
    if dir_x != 0 or dir_y != 0:
        frame = (frame + 1) % 8
    else:
        frame = 0

    x += dir_x * speed
    y += dir_y * speed

    # 화면 밖으로 못 나가게 제한 (캐릭터 크기 100 → 반폭 50)
    x = clamp(50, x, 800 - 50)
    y = clamp(50, y, 600 - 50)

    delay(0.03)


close_canvas()