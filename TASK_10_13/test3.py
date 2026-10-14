from pico2d import*
#게임 오브젝트 클래스 정의
class Grass:
    def __init__(self):
        self.image = load_image("grass.png")
    def draw(self):
        self.image.draw(400, 30)
    def update(self):
        pass

class Boy:
    def __init__(self):
        self.x, self.y = 100, 100
        self.frame = 0
        self.image = load_image("animation_sheet.png")
    def update(self):
        self.frame = (self.frame+1)%8
        self.x += 5
    def draw(self):
        self.image.clip_draw(self.frame*100, 0, 100, 100, self.x, self.y)

def handle_events():
    global running
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False

#월드 리셋
def reset_world():
    global running
    global grass
    global boy
    running = True
    grass = Grass()
    boy = Boy()

#월드 업데이트
def update_world():
    grass.update()
    boy.update()
    pass

#월드 렌더링
def render_world():
    clear_canvas()
    grass.draw()
    boy.draw()
    update_canvas()

open_canvas(800, 600)
reset_world()

while running:
    handle_events()
    update_world()
    render_world()
    delay(0.05)

close_canvas()