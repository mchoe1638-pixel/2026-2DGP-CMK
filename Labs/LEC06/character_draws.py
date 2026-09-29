from pico2d import *
import math
SPEED = 3

w = 800
h = 600
open_canvas(w, h)
grass = load_image('grass.png')
character = load_image('character.png')



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
    for x in range(400, 750+1, SPEED):
        draw_frame(x, 100)
    for y in range(100, 550+1, SPEED):
        draw_frame(750, y)
    for x in range(750, 50-1, -SPEED):
        draw_frame(x, 550)
    for y in range(550, 100-1, -SPEED):
        draw_frame(50, y)
    for x in range(50, 400+1, SPEED):
        draw_frame(x,100)
        
def move_triangle():
    for x in range(400, 750+1, SPEED):
        draw_frame(x, 100)
    for x in range(750, 400-1, -SPEED):
        y = 100 + (750 - x) * (450 / 350)
        draw_frame(x, y)
    for x in range(400, 50-1, -SPEED):
        y = 550 - (400 - x) * (450 / 350)
        draw_frame(x,y)
    for x in range(50, 400+1, SPEED):
        draw_frame(x,100)
while True:
    move_circle()
    move_rectangle()
    move_triangle()
