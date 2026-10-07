from pico2d import *


# ★ 배경 이미지(TUK_GROUND.png) 크기에 맞춰 창 크기 설정 (1280 x 1024)
TUK_WIDTH, TUK_HEIGHT = 1280, 1024
open_canvas(TUK_WIDTH, TUK_HEIGHT)

# ★ 이미지 불러오기
tuk_ground = load_image('TUK_GROUND.png')    # 배경
hand = load_image('hand_arrow.png')          # 마우스 커서 대신 그릴 손 이미지
character = load_image('animation_sheet.png')

# ★ 윈도우 기본 마우스 커서 숨기기 (안 숨기면 화살표 + 손 이미지가 같이 보임)
hide_cursor()


def handle_events():
    global running, target_x, target_y, mouse_x, mouse_y

    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False

        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False

        # ★ 마우스가 움직일 때마다 손 이미지 위치 갱신
        elif event.type == SDL_MOUSEMOTION:
            mouse_x = event.x
            mouse_y = TUK_HEIGHT - 1 - event.y     # y좌표 뒤집기

        # 클릭하면 그 위치를 캐릭터의 목표 지점으로
        elif event.type == SDL_MOUSEBUTTONDOWN:
            target_x = event.x
            target_y = TUK_HEIGHT - 1 - event.y


running = True
frame = 0

x, y = TUK_WIDTH // 2, TUK_HEIGHT // 2    # ★ 캐릭터 시작 위치 = 화면 중앙
target_x, target_y = x, y
mouse_x, mouse_y = x, y                   # ★ 손 이미지 위치 (처음엔 중앙)
speed = 8
face = 1


while running:
    clear_canvas()

    # ★ 1) 배경 먼저 그리기 - 화면 중앙에 그리면 창을 꽉 채움
    #    (그리는 순서 = 겹치는 순서. 먼저 그린 게 맨 뒤에 깔림)
    tuk_ground.draw(TUK_WIDTH // 2, TUK_HEIGHT // 2)

    # 2) 이동 계산
    dx = target_x - x
    dy = target_y - y
    distance = (dx ** 2 + dy ** 2) ** 0.5

    if distance > speed:
        x += dx / distance * speed
        y += dy / distance * speed
    else:
        x, y = target_x, target_y

    if dx > 0:
        face = 1
    elif dx < 0:
        face = 0

    # 3) 캐릭터 그리기 (배경 위)
    character.clip_draw(frame * 100, 100 * face, 100, 100, x, y)

    # ★ 4) 손 이미지는 맨 마지막에 그려야 캐릭터에 가려지지 않음
    hand.draw(mouse_x, mouse_y)

    update_canvas()
    handle_events()

    if distance > speed:
        frame = (frame + 1) % 8
    else:
        frame = 0

    delay(0.05)

close_canvas()