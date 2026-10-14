from pico2d import*

#배경클래스
class Grass:
    def __init__(self):
        self.image = load_image("grass.png")
    def update(self):
        pass
    def draw(self):
        self.image.draw(400, 40)
#캐릭터클래스
class Boy:
    def __init__(self):
        self.image = load_image("animation_sheet.png")

        self.x, self.y = 100, 100

        self.dir_x, self.dir_y = 0, 0

        self.face = 1

        self.COLS, self.ROWS, self.col, self.row = 8, 4, 0, 0

        self.speed, self.tick = 5, 0

        self.frame_w = self.image.w // self.COLS
        self.frame_h = self.image.h // self.ROWS

        self.moving = 0
    def update(self):
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed
        if self.dir_x != 0:
            self.face = self.dir_x
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
        if self.tick % 5 == 0:
            self.col = (self.col + 1) % self.COLS
    def draw(self):
        self.image.clip_draw(self.col*self.frame_w, self.row*self.frame_h, self.frame_w, self.frame_h, self.x, self.y)


#입력함수
def handle_event():
    global running
    
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_RIGHT: boy.dir_x += 1
            elif event.key == SDLK_LEFT: boy.dir_x -= 1
            elif event.key == SDLK_UP: boy.dir_y += 1
            elif event.key == SDLK_DOWN: boy.dir_y -= 1
        elif event.type == SDL_KEYUP:
            if event.key == SDLK_RIGHT: boy.dir_x -= 1
            elif event.key == SDLK_LEFT: boy.dir_x += 1
            elif event.key == SDLK_UP: boy.dir_y -= 1
            elif event.key == SDLK_DOWN: boy.dir_y += 1

#월드초기화함수
def reset_world():
    global running, grass, boy
    running = True
    grass = Grass()
    boy = Boy()
#월드업데이트함수
def update_world():
    boy.update()

#월드렌더링함수
def render_world():
    clear_canvas()
    grass.draw()
    boy.draw()
    update_canvas()

open_canvas(800, 600)
reset_world()

while running:
    handle_event()
    update_world()
    render_world()
    delay(0.05)

close_canvas()