from pico2d import *
import random


class Grass:
    def __init__(self):
        self.image = load_image('grass.png')

    def draw(self):
        self.image.draw(400, 30)

    def update(self):
        pass
class Zombie:
    def __init__(self):
        self.x, self.y = 100, 170
        self.frame = 0
        self.image = load_image('zombie.png')

    def update(self):
        self.frame = (self.frame + 1)%10
        self.x +=5

    def draw(self):
        frame_width = self.image.w//10
        frame_height = self.image.h
        self.image.clip_draw(self.frame * frame_width, 0, frame_width, frame_height,
                             self.x, self.y, frame_width//2, frame_height//2)
    

class Boy:
    def __init__(self):
        self.x, self.y = random.randint(100, 700), 90   # 시작 위치를 흩뿌림
        self.frame = random.randint(0, 7)                # 애니메이션 박자도 엇갈리게
        self.image = load_image('run_animation.png')

    def update(self):
        self.frame = (self.frame + 1) % 8
        self.x += 5

    def draw(self):
        self.image.clip_draw(self.frame * 100, 0, 100, 100, self.x, self.y)


def handle_events():
    global running
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:                                   # 창 X 버튼
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:  # ESC 키
            running = False


def reset_world():
    global running, grass, team, zombie     # team도 global로 선언
    running = True
    grass = Grass()
    zombie = Zombie()
    team = [Boy() for i in range(11)]


def update_world():
    grass.update()
    for boy in team:
        boy.update()              # 클래스(Grass)가 아니라 인스턴스(grass)로 호출
    zombie.update()


def render_world():
    clear_canvas()
    grass.draw()
    for boy in team:
        boy.draw()  
    zombie.draw()
    update_canvas()


open_canvas()
reset_world()      # 이미지 로딩은 반드시 open_canvas() 다음에

while running:
    handle_events()
    update_world()
    render_world()
    delay(0.05)

close_canvas()