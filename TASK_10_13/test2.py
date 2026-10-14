from pico2d import *
import random
class Grass:
    def __init__(self):
        self.image = load_image("grass.png")
    def draw(self):
        self.image.draw(400, 30)
    def update(self):
        pass

class Boy:
    def __init__(self):
        self.image = load_image("animation_sheet.png")
        self.x, self.y = 400, 90
        self.dir_x, self.dir_y = 0, 0
        self.face = 1                      # 1=오른쪽, -1=왼쪽
        self.COLS, self.ROWS = 8, 4
        self.frame_w = self.image.w // self.COLS
        self.frame_h = self.image.h // self.ROWS
        self.col, self.row = 0, 3
        self.speed = 5
        self.tick = 0

    def update(self):
        self.x += self.dir_x * self.speed          # ⑤ 누적
        self.y += self.dir_y * self.speed
        self.x = clamp(25, self.x, 800 - 25)       # 화면 밖 탈출 방지
        self.y = clamp(50, self.y, 600 - 50)

        if self.dir_x != 0:
            self.face = self.dir_x                 # ② self. 붙이기

        self.moving = self.dir_x != 0 or self.dir_y != 0
        if self.moving != 0:
            if self.face == 1:
                self.row = 1
            else:
                self.row = 0
        else:
            if self.face == 1:
                self.row = 3
            else:
                self.row = 2
        self.tick += 1
        if self.tick % 2 == 0:
            self.col = (self.col + 1) % self.COLS

    def draw(self):
        self.image.clip_draw(self.col * self.frame_w, self.row * self.frame_h,
                             self.frame_w, self.frame_h, self.x, self.y)

class Zombie:
    def __init__(self):
        self.x, self.y = random.randint(100, 700), 170
        self.frame = random.randint(0, 9)
        self.image = load_image("zombie_run_animation.png")
        self.frame_w = self.image.w // 10
        self.frame_h = self.image.h
    def update(self):
        self.frame = (self.frame + 1) % 10
        self.x += 5
        if self.x > 800 + self.frame_w // 4:      # ④ 오른쪽 끝을 넘으면 왼쪽에서 재등장
            self.x = -self.frame_w // 4
    def draw(self):
        self.image.clip_draw(self.frame * self.frame_w, 0, self.frame_w, self.frame_h, self.x, self.y, self.frame_w//2, self.frame_h//2)
        

def handle():
    global running
    for event in get_events():                     # ④ 0 초기화 삭제
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE: running = False
            elif event.key == SDLK_RIGHT: boy.dir_x += 1   # ② boy에 직접
            elif event.key == SDLK_LEFT:  boy.dir_x -= 1
            elif event.key == SDLK_UP:    boy.dir_y += 1
            elif event.key == SDLK_DOWN:  boy.dir_y -= 1
        elif event.type == SDL_KEYUP:                  # ③ KEYUP
            if event.key == SDLK_RIGHT:   boy.dir_x -= 1
            elif event.key == SDLK_LEFT:  boy.dir_x += 1
            elif event.key == SDLK_UP:    boy.dir_y -= 1
            elif event.key == SDLK_DOWN:  boy.dir_y += 1

def reset_world():
    global running, grass, boy, zombie
    running = True
    grass = Grass()
    boy = Boy()
    zombie = Zombie()
    global team
    team = [Zombie() for i in range(11)]

def update_world():
    boy.update()
    for zombie in team:
        zombie.update()

def render_world():
    clear_canvas()
    grass.draw()
    boy.draw()
    for zombie in team:
        zombie.draw()
    update_canvas()

open_canvas(800, 600)   # ① 캔버스 먼저
reset_world()

while running:
    handle()
    update_world()
    render_world()
    delay(0.03)

close_canvas()

# class Boy:
#     def __init__(self):
#         self.image = load_image("animation_sheet.png")
#         self.x, self.y = 400, 90
#         self.target_x, self.target_y = self.x, self.y   # 목적지 = 현재 위치 → 정지 상태
#         self.face = 1
#         self.COLS, self.ROWS = 8, 4
#         self.frame_w = self.image.w // self.COLS
#         self.frame_h = self.image.h // self.ROWS
#         self.col, self.row = 0, 3
#         self.speed = 5
#         self.tick = 0
#         self.moving = False

#     def set_target(self, x, y):
#         self.target_x = clamp(25, x, 800 - 25)          # 화면 밖은 목적지로 못 찍게
#         self.target_y = clamp(50, y, 600 - 50)

#     def update(self):
#         dx = self.target_x - self.x
#         dy = self.target_y - self.y
#         dist = (dx * dx + dy * dy) ** 0.5

#         if dist <= self.speed:                          # 거의 도착 → 스냅 후 정지
#             self.x, self.y = self.target_x, self.target_y
#             self.moving = False
#         else:
#             self.x += dx / dist * self.speed            # 정규화 × 속도
#             self.y += dy / dist * self.speed
#             self.moving = True
#             if dx != 0:
#                 self.face = 1 if dx > 0 else -1

#         if self.moving:
#             self.row = 1 if self.face == 1 else 0
#         else:
#             self.row = 3 if self.face == 1 else 2

#         self.tick += 1
#         if self.tick % 2 == 0:
#             self.col = (self.col + 1) % self.COLS

#     def draw(self):
#         self.image.clip_draw(self.col * self.frame_w, self.row * self.frame_h,
#                              self.frame_w, self.frame_h, self.x, self.y)


# def handle():
#     global running
#     for event in get_events():
#         if event.type == SDL_QUIT:
#             running = False
#         elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
#             running = False
#         elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
#             boy.set_target(event.x, 600 - 1 - event.y)  # y축 뒤집기