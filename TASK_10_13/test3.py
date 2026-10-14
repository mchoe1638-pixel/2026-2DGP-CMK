from pico2d import *
import random
class Grass:
    def __init__(self): #소스
        self.image = load_image("grass.png")
    def draw(self): #렌더링
        self.image.draw(400, 30)
    def update(self): #업데이트
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
        
 
def handle(): #입력
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

def reset_world(): #초기화
    global running, grass, boy, zombie
    running = True
    grass = Grass()
    boy = Boy()
    zombie = Zombie()
    global team
    team = [Zombie() for i in range(11)]

def update_world(): #업데이트
    boy.update()
    for zombie in team:
        zombie.update()

def render_world(): #렌더링
    clear_canvas()
    grass.draw()
    boy.draw()
    for zombie in team:
        zombie.draw()
    update_canvas()

open_canvas(800, 600)   # ① 캔버스 먼저
reset_world()

while running:
    handle() #입력
    update_world() #업데이트
    render_world() #렌더링
    delay(0.03) #딜레이

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


# from pico2d import *
# import math
# SPEED = 3
# LEFT, RIGHT, TOP, BOTTOM = 50, 750, 550, 100
# w = 800
# h = 600
# open_canvas(w, h)
# grass = load_image('grass.png')
# character = load_image('character.png')

# running = True

# def handle_events():
#     global running
#     for event in get_events():
#         if event.type == SDL_QUIT:
#             running = False
#         elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
#             running = False

# def draw_frame(x,y):
#     get_events()
#     clear_canvas()
#     grass.draw(w//2, h//8)
#     character.draw(x,y)
#     update_canvas()
#     delay(0.01)

# def move_circle():
#     CENTER_X = 400
#     CENTER_Y = 300
#     RADIUS = 200
#     angle = 270
#     for angle in range(270, 270 + 360 + 1, 2):
#         x = CENTER_X+RADIUS*math.cos(math.radians(angle))
#         y = CENTER_Y+RADIUS*math.sin(math.radians(angle))        
#         draw_frame(x,y)
#         if not running: return

# def move_rectangle():
#     CENTER_X = w // 2
#     for x in range(CENTER_X, RIGHT+1, SPEED):
#         draw_frame(x, BOTTOM)
#         if not running: return
#     for y in range(BOTTOM, TOP+1, SPEED):
#         draw_frame(RIGHT, y)
#         if not running: return
#     for x in range(RIGHT, LEFT-1, -SPEED):
#         draw_frame(x, TOP)
#         if not running: return
#     for y in range(TOP, BOTTOM-1, -SPEED):
#         draw_frame(LEFT, y)
#         if not running: return
#     for x in range(LEFT, CENTER_X+1, SPEED):
#         draw_frame(x,BOTTOM)
#         if not running: return
        
# def move_triangle():
#     CENTER_X = w // 2
#     slope = (TOP - BOTTOM) / (RIGHT - CENTER_X)
#     for x in range(CENTER_X, RIGHT+1, SPEED):
#         draw_frame(x, BOTTOM)
#         if not running: return
#     for x in range(RIGHT, CENTER_X-1, -SPEED):
#         y = 100 + (RIGHT - x) * slope
#         draw_frame(x, y)
#         if not running: return
#     for x in range(CENTER_X, LEFT-1, -SPEED):
#         y = TOP - (CENTER_X - x) * slope
#         draw_frame(x,y)
#         if not running: return
#     for x in range(LEFT, CENTER_X+1, SPEED):
#         draw_frame(x,BOTTOM)
#         if not running: return

# while running:
#     move_circle()
#     delay(0.3)
#     move_rectangle()
#     delay(0.3)
#     move_triangle()
#     delay(0.3)

# twice = ['momo', 'sana', 'zwi', 'nayun', 'dahyun']
# black_pink = ['jisu', 'jeni', 'rose', 'risa']
# print(twice)
# twice.append('jihyo')
# print(twice)
# twice.sort()
# print(twice)
# print(len(twice))
# unite = twice + black_pink
# print(unite)
# unite.remove('momo')
# print(unite)
# # 17쪽
# print(unite[0])
# print(unite[-1])
# print(unite[:3])
# print(unite[-3:])