from pico2d import *
import math
SPEED = 3
LEFT, RIGHT, TOP, BOTTOM = 50, 750, 550, 100
w = 800
h = 600
open_canvas(w, h)
grass = load_image('grass.png')
character = load_image('character.png')

running = True

def handle_events():
    global running
    for event in get_events():
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False

def draw_frame(x,y):
    get_events()
    clear_canvas()
    grass.draw(w//2, h//8)
    character.draw(x,y)
    update_canvas()
    delay(0.01)

def move_circle():
    CENTER_X = 400
    CENTER_Y = 300
    RADIUS = 200
    angle = 270
    for angle in range(270, 270 + 360 + 1, 2):
        x = CENTER_X+RADIUS*math.cos(math.radians(angle))
        y = CENTER_Y+RADIUS*math.sin(math.radians(angle))        
        draw_frame(x,y)

def move_rectangle():
    CENTER_X = w // 2
    for x in range(CENTER_X, RIGHT+1, SPEED):
        draw_frame(x, BOTTOM)
    for y in range(BOTTOM, TOP+1, SPEED):
        draw_frame(RIGHT, y)
    for x in range(RIGHT, LEFT-1, -SPEED):
        draw_frame(x, TOP)
    for y in range(TOP, BOTTOM-1, -SPEED):
        draw_frame(LEFT, y)
    for x in range(LEFT, CENTER_X+1, SPEED):
        draw_frame(x,BOTTOM)
        
def move_triangle():
    CENTER_X = w // 2
    slope = (TOP - BOTTOM) / (RIGHT - CENTER_X)
    for x in range(CENTER_X, RIGHT+1, SPEED):
        draw_frame(x, BOTTOM)
    for x in range(RIGHT, CENTER_X-1, -SPEED):
        y = 100 + (RIGHT - x) * slope
        draw_frame(x, y)
    for x in range(CENTER_X, LEFT-1, -SPEED):
        y = TOP - (CENTER_X - x) * slope
        draw_frame(x,y)
    for x in range(LEFT, CENTER_X+1, SPEED):
        draw_frame(x,BOTTOM)
while True:
    move_circle()
    move_rectangle()
    move_triangle()
