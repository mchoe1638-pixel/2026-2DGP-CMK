import math
from pico2d import *

W, H = 800, 600
SPEED = 3            # 프레임당 이동 거리(px) - 모든 운동 공통
FRAME_DELAY = 0.01

CX, CY, R = W // 2, 300, 200
LEFT, RIGHT, TOP, BOTTOM = 50, 750, 550, CY - R
START = (CX, BOTTOM)   # (400, 100): 원의 맨 아래 = 모든 운동의 시작/끝점

RECTANGLE = [START, (RIGHT, BOTTOM), (RIGHT, TOP), (LEFT, TOP), (LEFT, BOTTOM), START]
TRIANGLE  = [START, (RIGHT, BOTTOM), (CX, TOP), (LEFT, BOTTOM), START]


def circle_points():
    steps = int(2 * math.pi * R / SPEED)      # 둘레 ÷ 속도 → 원도 같은 속도로
    for i in range(steps):
        a = math.radians(270) + 2 * math.pi * i / steps
        yield CX + R * math.cos(a), CY + R * math.sin(a)


def path_points(vertices):
    for (x1, y1), (x2, y2) in zip(vertices, vertices[1:]):
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / SPEED))
        for i in range(steps):
            t = i / steps                     # 0.0 → 1.0 진행률
            yield x1 + (x2 - x1) * t, y1 + (y2 - y1) * t


def one_cycle():
    yield from circle_points()
    yield from path_points(RECTANGLE)
    yield from path_points(TRIANGLE)


def is_running():
    for e in get_events():
        if e.type == SDL_QUIT or (e.type == SDL_KEYDOWN and e.key == SDLK_ESCAPE):
            return False
    return True


open_canvas(W, H)
grass = load_image('grass.png')
character = load_image('character.png')


def main():
    while True:
        for x, y in one_cycle():
            if not is_running():
                return
            clear_canvas()
            grass.draw(W // 2, H // 8)
            character.draw(x, y)
            update_canvas()
            delay(FRAME_DELAY)


main()
close_canvas()