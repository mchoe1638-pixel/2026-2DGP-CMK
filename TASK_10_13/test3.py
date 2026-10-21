from pico2d import *

def handle_event():
    global running
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.key == SDLK_ESCAPE:
            running = False

class Boy:
    def __init__(self):
        image = load_image('animation_sheet')
        spawn_x, spawn_y = 100, 100
    def update(self):
        pass
    def render(self):


open_canvas()
running = True

while running:
