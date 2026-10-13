from pico2d import *

class Grass:
    def __init__(self):
        self.image = load_image("grass.png")

    def draw(self):
        self.image.draw(400, 30)

    def updata(self):
        pass

class Boy:
    def __init__(self):
        self.x, self.y = 0,90
        self.frame = 0
        self.image = load_image('run_animation.png')
    def updata(self):
        self.frame = (self.frame+1)%8
        self.x +=5
    def draw(self):
        self.image.clip_draw(self.frame*100, 0, 100, 100, self.x, self.y)



def reset_world():
    global running
    running = True
    Grass.updata()
    Boy.updata()

def update_world():
    Grass.draw()
    Boy.draw()
    pass

def render_world():
    clear_canvas()
    update_canvas()

def handle_events():
    pass

open_canvas()

reset_world()

while running:
    handle_events()
    update_world()
    render_world()
    delay(0.05)

close_canvas()

#게임 루프를 간략하게 정리한 코드